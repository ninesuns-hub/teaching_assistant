import unittest
from types import SimpleNamespace
from unittest.mock import ANY, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.learning_service import (
    REPORT_INPUT_CHAR_LIMIT,
    _bound_report_messages,
)
from app.services import learning_jobs
from database import learning_repo
from database.mysql_db import LearningGenerationJob


class ReportInputTests(unittest.TestCase):
    def test_report_input_keeps_newest_messages_in_chronological_order(self):
        messages = [
            {"role": "user", "content": "old" * 20_000},
            {"role": "assistant", "content": "middle" * 5_000},
            {"role": "user", "content": "newest"},
        ]

        selected, truncated = _bound_report_messages(messages)

        self.assertTrue(truncated)
        self.assertEqual(selected[-1]["content"], "newest")
        self.assertLessEqual(
            sum(len(message["content"]) + 32 for message in selected),
            REPORT_INPUT_CHAR_LIMIT,
        )

    def test_oversized_latest_message_is_trimmed_from_the_end(self):
        content = "a" * REPORT_INPUT_CHAR_LIMIT + "LATEST"

        selected, truncated = _bound_report_messages([
            {"role": "user", "content": content},
        ])

        self.assertTrue(truncated)
        self.assertEqual(len(selected), 1)
        self.assertTrue(selected[0]["content"].endswith("LATEST"))
        self.assertEqual(len(selected[0]["content"]), REPORT_INPUT_CHAR_LIMIT)


class LearningJobWorkerTests(unittest.TestCase):
    class FakeDb:
        def __init__(self):
            self.commits = 0
            self.rollbacks = 0
            self.closed = False

        def commit(self):
            self.commits += 1

        def rollback(self):
            self.rollbacks += 1

        def close(self):
            self.closed = True

    def test_student_job_persists_result_and_completes_atomically(self):
        db = self.FakeDb()
        job = SimpleNamespace(
            id="job-1",
            kind=learning_jobs.STUDENT_REPORT_JOB,
            class_id=7,
            student_id=9,
            requested_by=9,
        )
        with (
            patch.object(learning_jobs, "SessionLocal", return_value=db),
            patch.object(learning_jobs.learning_repo, "claim_learning_job", return_value=True),
            patch.object(learning_jobs.learning_repo, "get_learning_job", return_value=job),
            patch.object(
                learning_jobs,
                "generate_student_report_record",
                return_value={"id": 42},
            ) as generate,
            patch.object(learning_jobs.learning_repo, "complete_learning_job") as complete,
            patch.object(learning_jobs.learning_repo, "fail_learning_job") as fail,
        ):
            learning_jobs._run_learning_job("job-1")

        generate.assert_called_once_with(db, 9, 7, 9, commit=False)
        complete.assert_called_once_with(db, job, 42)
        fail.assert_not_called()
        self.assertEqual(db.commits, 1)
        self.assertTrue(db.closed)

    def test_failed_generation_marks_job_failed_without_result(self):
        db = self.FakeDb()
        job = SimpleNamespace(
            id="job-2",
            kind=learning_jobs.STUDENT_REPORT_JOB,
            class_id=7,
            student_id=9,
            requested_by=9,
        )
        with (
            patch.object(learning_jobs, "SessionLocal", return_value=db),
            patch.object(learning_jobs.learning_repo, "claim_learning_job", return_value=True),
            patch.object(learning_jobs.learning_repo, "get_learning_job", return_value=job),
            patch.object(
                learning_jobs,
                "generate_student_report_record",
                side_effect=RuntimeError("provider secret"),
            ),
            patch.object(learning_jobs.learning_repo, "complete_learning_job") as complete,
            patch.object(learning_jobs.learning_repo, "fail_learning_job") as fail,
        ):
            learning_jobs._run_learning_job("job-2")

        complete.assert_not_called()
        fail.assert_called_once_with(db, "job-2", "报告整理失败，请稍后重试")
        self.assertGreaterEqual(db.rollbacks, 1)
        self.assertTrue(db.closed)

    def test_recovery_resubmits_incomplete_jobs(self):
        db = self.FakeDb()
        with (
            patch.object(learning_jobs, "SessionLocal", return_value=db),
            patch.object(
                learning_jobs.learning_repo,
                "recover_learning_jobs",
                return_value=["job-a", "job-b"],
            ),
            patch.object(learning_jobs, "submit_learning_job") as submit,
        ):
            count = learning_jobs.recover_incomplete_learning_jobs()

        self.assertEqual(count, 2)
        self.assertEqual(
            [call.args[0] for call in submit.call_args_list],
            ["job-a", "job-b"],
        )
        self.assertTrue(db.closed)


class LearningJobRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        LearningGenerationJob.__table__.create(self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_duplicate_active_job_is_reused_then_released_on_completion(self):
        first, first_created = learning_repo.enqueue_learning_job(
            self.db,
            kind=learning_jobs.STUDENT_REPORT_JOB,
            class_id=3,
            student_id=5,
            requested_by=5,
            dedupe_key="student-report:3:5",
        )
        duplicate, duplicate_created = learning_repo.enqueue_learning_job(
            self.db,
            kind=learning_jobs.STUDENT_REPORT_JOB,
            class_id=3,
            student_id=5,
            requested_by=5,
            dedupe_key="student-report:3:5",
        )

        self.assertTrue(first_created)
        self.assertFalse(duplicate_created)
        self.assertEqual(first.id, duplicate.id)
        self.assertTrue(learning_repo.claim_learning_job(self.db, first.id))

        current = learning_repo.get_learning_job(self.db, first.id)
        learning_repo.complete_learning_job(self.db, current, 11)
        self.db.commit()
        replacement, replacement_created = learning_repo.enqueue_learning_job(
            self.db,
            kind=learning_jobs.STUDENT_REPORT_JOB,
            class_id=3,
            student_id=5,
            requested_by=5,
            dedupe_key="student-report:3:5",
        )

        self.assertTrue(replacement_created)
        self.assertNotEqual(first.id, replacement.id)


class LearningJobRouteTests(unittest.TestCase):
    def test_job_status_rejects_another_user(self):
        from fastapi import HTTPException
        from app.interfaces.api import learning_routes

        foreign_job = SimpleNamespace(requested_by=88)
        with patch.object(
            learning_routes.learning_repo,
            "get_learning_job",
            return_value=foreign_job,
        ):
            with self.assertRaises(HTTPException) as raised:
                learning_routes.get_learning_generation_job(
                    "job-private",
                    current_user=SimpleNamespace(id=77),
                    db=SimpleNamespace(),
                )

        self.assertEqual(raised.exception.status_code, 403)

    def test_student_cannot_regenerate_without_new_messages(self):
        from fastapi import HTTPException
        from app.interfaces.api import learning_routes

        report = SimpleNamespace(message_count=12)
        with (
            patch.object(
                learning_routes.class_repo,
                "user_can_access_class",
                return_value=True,
            ),
            patch.object(
                learning_routes.learning_repo,
                "list_student_reports",
                return_value=[report],
            ),
            patch.object(
                learning_routes.conversation_repo,
                "count_student_messages_in_class",
                return_value=12,
            ),
            patch.object(learning_routes, "enqueue_student_report") as enqueue,
        ):
            with self.assertRaises(HTTPException) as raised:
                learning_routes.create_my_report(
                    class_id=3,
                    current_user=SimpleNamespace(id=7),
                    db=SimpleNamespace(),
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(
            raised.exception.detail,
            "暂无新的学习记录，请先继续学习交流",
        )
        enqueue.assert_not_called()

    def test_student_can_update_after_a_new_message(self):
        from app.interfaces.api import learning_routes

        report = SimpleNamespace(message_count=12)
        job = SimpleNamespace(id="job-new")
        with (
            patch.object(
                learning_routes.class_repo,
                "user_can_access_class",
                return_value=True,
            ),
            patch.object(
                learning_routes.learning_repo,
                "list_student_reports",
                return_value=[report],
            ),
            patch.object(
                learning_routes.conversation_repo,
                "count_student_messages_in_class",
                return_value=13,
            ),
            patch.object(
                learning_routes,
                "enqueue_student_report",
                return_value=job,
            ) as enqueue,
            patch.object(
                learning_routes,
                "serialize_learning_job",
                return_value={"id": "job-new", "status": "queued"},
            ),
        ):
            response = learning_routes.create_my_report(
                class_id=3,
                current_user=SimpleNamespace(id=7),
                db=SimpleNamespace(),
            )

        self.assertEqual(response["id"], "job-new")
        enqueue.assert_called_once_with(
            ANY,
            class_id=3,
            student_id=7,
            requested_by=7,
        )


if __name__ == "__main__":
    unittest.main()
