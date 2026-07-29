import asyncio
from io import BytesIO
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.interfaces.api import homework_routes
from database import homework_repo
from database.mysql_db import (
    Base,
    ClassMember,
    ClassRoom,
    HomeworkSubmissionAttachment,
    User,
    UserRole,
)


class HomeworkSubmissionAttachmentTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.teacher = User(
            email="1000001@tongji.edu.cn",
            name="Teacher",
            hashed_password="x",
            role=UserRole.TEACHER,
        )
        self.student = User(
            email="1000002@tongji.edu.cn",
            name="Student",
            hashed_password="x",
            role=UserRole.STUDENT,
        )
        self.other_student = User(
            email="1000003@tongji.edu.cn",
            name="Other",
            hashed_password="x",
            role=UserRole.STUDENT,
        )
        self.db.add_all([self.teacher, self.student, self.other_student])
        self.db.flush()
        self.classroom = ClassRoom(
            name="Class A",
            invite_code="ABC123",
            teacher_id=self.teacher.id,
        )
        self.db.add(self.classroom)
        self.db.flush()
        self.db.add(ClassMember(
            class_id=self.classroom.id,
            student_id=self.student.id,
        ))
        self.db.commit()
        self.homework = homework_repo.create_homework(
            self.db,
            class_id=self.classroom.id,
            title="Homework",
            description="",
            due_at=None,
            created_by=self.teacher.id,
        )
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()
        self.db.close()
        self.engine.dispose()

    def _upload(self, filename: str, content: bytes = b"content") -> UploadFile:
        return UploadFile(filename=filename, file=BytesIO(content))

    def _saved_path(self, filename: str) -> str:
        path = Path(self.temp_dir.name, filename)
        path.write_bytes(b"saved")
        return str(path)

    def test_multiple_files_are_saved_and_serialized(self):
        paths = [self._saved_path("one.pdf"), self._saved_path("two.docx")]
        with patch.object(
            homework_routes.data_manager,
            "save_submission_attachment",
            side_effect=[
                {"status": "success", "path": paths[0]},
                {"status": "success", "path": paths[1]},
            ],
        ):
            result = asyncio.run(homework_routes.submit_homework(
                homework_id=self.homework.id,
                content="My work",
                files=[self._upload("one.pdf"), self._upload("two.docx")],
                file=None,
                retained_attachment_ids="[]",
                current_user=self.student,
                db=self.db,
            ))

        self.assertEqual(len(result.attachments), 2)
        self.assertEqual(result.filename, "one.pdf")
        stored = self.db.query(HomeworkSubmissionAttachment).all()
        self.assertEqual([item.filename for item in stored], ["one.pdf", "two.docx"])

    def test_resubmit_can_retain_remove_and_add(self):
        sub, _ = homework_repo.save_submission_with_attachments(
            self.db,
            self.homework.id,
            self.student.id,
            "first",
            set(),
            [
                {"filename": "keep.pdf", "file_path": self._saved_path("keep.pdf"), "file_type": "pdf", "file_size": 10},
                {"filename": "remove.pdf", "file_path": self._saved_path("remove.pdf"), "file_type": "pdf", "file_size": 10},
            ],
        )
        original = homework_repo.list_submission_attachments(self.db, sub.id)
        new_path = self._saved_path("new.pdf")
        with (
            patch.object(
                homework_routes.data_manager,
                "save_submission_attachment",
                return_value={"status": "success", "path": new_path},
            ),
            patch.object(homework_routes.settings, "HOMEWORK_DIR", self.temp_dir.name),
        ):
            result = asyncio.run(homework_routes.submit_homework(
                homework_id=self.homework.id,
                content="updated",
                files=[self._upload("new.pdf")],
                file=None,
                retained_attachment_ids=f"[{original[0].id}]",
                current_user=self.student,
                db=self.db,
            ))

        self.assertEqual([item.filename for item in result.attachments], ["keep.pdf", "new.pdf"])
        self.assertFalse(Path(self.temp_dir.name, "remove.pdf").exists())

    def test_limits_file_count_and_size(self):
        uploads = [self._upload(f"{index}.pdf") for index in range(6)]
        with self.assertRaises(HTTPException) as count_error:
            asyncio.run(homework_routes.submit_homework(
                homework_id=self.homework.id,
                content="",
                files=uploads,
                file=None,
                retained_attachment_ids="[]",
                current_user=self.student,
                db=self.db,
            ))
        self.assertEqual(count_error.exception.status_code, 400)

        with (
            patch.object(homework_routes, "MAX_SUBMISSION_FILE_SIZE", 4),
            self.assertRaises(HTTPException) as size_error,
        ):
            asyncio.run(homework_routes.submit_homework(
                homework_id=self.homework.id,
                content="",
                files=[self._upload("large.pdf", b"12345")],
                file=None,
                retained_attachment_ids="[]",
                current_user=self.student,
                db=self.db,
            ))
        self.assertEqual(size_error.exception.status_code, 400)

        with (
            patch.object(homework_routes, "MAX_SUBMISSION_FILE_SIZE", 10),
            patch.object(homework_routes, "MAX_SUBMISSION_TOTAL_SIZE", 8),
            self.assertRaises(HTTPException) as total_error,
        ):
            asyncio.run(homework_routes.submit_homework(
                homework_id=self.homework.id,
                content="",
                files=[
                    self._upload("first.pdf", b"12345"),
                    self._upload("second.pdf", b"67890"),
                ],
                file=None,
                retained_attachment_ids="[]",
                current_user=self.student,
                db=self.db,
            ))
        self.assertEqual(total_error.exception.status_code, 400)

    def test_rejects_invalid_retained_attachment_ids(self):
        with self.assertRaises(HTTPException) as invalid_id:
            asyncio.run(homework_routes.submit_homework(
                homework_id=self.homework.id,
                content="updated",
                files=None,
                file=None,
                retained_attachment_ids="[999999]",
                current_user=self.student,
                db=self.db,
            ))
        self.assertEqual(invalid_id.exception.status_code, 400)

    def test_attachment_preview_enforces_submission_access(self):
        path = self._saved_path("preview.pdf")
        sub, _ = homework_repo.save_submission_with_attachments(
            self.db,
            self.homework.id,
            self.student.id,
            "preview",
            set(),
            [{"filename": "preview.pdf", "file_path": path, "file_type": "pdf", "file_size": 10}],
        )
        attachment = homework_repo.list_submission_attachments(self.db, sub.id)[0]

        with patch.object(homework_routes.settings, "HOMEWORK_DIR", self.temp_dir.name):
            response = homework_routes.get_submission_attachment_file(
                submission_id=sub.id,
                attachment_id=attachment.id,
                download=False,
                current_user=self.teacher,
                db=self.db,
            )
            self.assertEqual(response.media_type, "application/pdf")

            with self.assertRaises(HTTPException) as denied:
                homework_routes.get_submission_attachment_file(
                    submission_id=sub.id,
                    attachment_id=attachment.id,
                    download=False,
                    current_user=self.other_student,
                    db=self.db,
                )
        self.assertEqual(denied.exception.status_code, 403)

    def test_attachment_preview_rejects_paths_outside_homework_storage(self):
        outside_dir = tempfile.TemporaryDirectory()
        self.addCleanup(outside_dir.cleanup)
        outside_path = Path(outside_dir.name, "outside.pdf")
        outside_path.write_bytes(b"outside")
        sub, _ = homework_repo.save_submission_with_attachments(
            self.db,
            self.homework.id,
            self.student.id,
            "preview",
            set(),
            [{
                "filename": "outside.pdf",
                "file_path": str(outside_path),
                "file_type": "pdf",
                "file_size": 7,
            }],
        )
        attachment = homework_repo.list_submission_attachments(self.db, sub.id)[0]

        with (
            patch.object(homework_routes.settings, "HOMEWORK_DIR", self.temp_dir.name),
            self.assertRaises(HTTPException) as denied,
        ):
            homework_routes.get_submission_attachment_file(
                submission_id=sub.id,
                attachment_id=attachment.id,
                download=False,
                current_user=self.student,
                db=self.db,
            )
        self.assertEqual(denied.exception.status_code, 404)

    def test_deleting_homework_removes_every_submission_attachment_file(self):
        paths = [
            self._saved_path("first.pdf"),
            self._saved_path("second.pdf"),
        ]
        homework_repo.save_submission_with_attachments(
            self.db,
            self.homework.id,
            self.student.id,
            "submitted",
            set(),
            [
                {"filename": "first.pdf", "file_path": paths[0], "file_type": "pdf", "file_size": 5},
                {"filename": "second.pdf", "file_path": paths[1], "file_type": "pdf", "file_size": 6},
            ],
        )

        with patch.object(homework_routes.settings, "HOMEWORK_DIR", self.temp_dir.name):
            result = homework_routes.delete_homework(
                homework_id=self.homework.id,
                current_user=self.teacher,
                db=self.db,
            )

        self.assertEqual(result, {"ok": True})
        self.assertFalse(Path(paths[0]).exists())
        self.assertFalse(Path(paths[1]).exists())


class HomeworkSubmissionAttachmentMigrationTests(unittest.TestCase):
    def test_upgrade_backfills_legacy_attachment_and_is_idempotent(self):
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "alembic"
            / "versions"
            / "20260729_0004_submission_attachments.py"
        )
        spec = importlib.util.spec_from_file_location(
            "submission_attachment_migration",
            migration_path,
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)

        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as connection:
            connection.connection.create_function(
                "SUBSTRING_INDEX",
                3,
                lambda value, delimiter, count: (
                    value.rsplit(delimiter, 1)[-1] if value else None
                ),
            )
            connection.execute(text(
                """
                CREATE TABLE homework_submissions (
                    id INTEGER PRIMARY KEY,
                    filename VARCHAR(255),
                    file_path VARCHAR(500),
                    file_type VARCHAR(20),
                    file_size BIGINT,
                    submitted_at DATETIME
                )
                """
            ))
            connection.execute(
                text(
                    """
                    INSERT INTO homework_submissions
                        (id, filename, file_path, file_type, file_size, submitted_at)
                    VALUES
                        (1, 'legacy.pdf', '/app/storage/legacy.pdf', 'pdf', 128, NULL)
                    """
                )
            )
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()
            migration.upgrade()

            rows = connection.execute(text(
                """
                SELECT submission_id, filename, file_path, file_type, file_size
                FROM homework_submission_attachments
                """
            )).mappings().all()
            indexes = {
                item["name"]
                for item in inspect(connection).get_indexes(
                    "homework_submission_attachments"
                )
            }

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["submission_id"], 1)
        self.assertEqual(rows[0]["filename"], "legacy.pdf")
        self.assertIn("ix_homework_submission_attachments_id", indexes)
        self.assertIn(
            "ix_homework_submission_attachments_submission_id",
            indexes,
        )
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
