"""Persistent background jobs for learning reports and class feedback."""

from concurrent.futures import ThreadPoolExecutor
import logging
import time
from typing import Optional

from sqlalchemy.orm import Session

from database.mysql_db import LearningGenerationJob, SessionLocal
from database import learning_repo
from app.services.learning_service import (
    generate_class_feedback_record,
    generate_student_report_record,
    _serialize_feedback,
    _serialize_report,
)

logger = logging.getLogger(__name__)

STUDENT_REPORT_JOB = "student_report"
CLASS_FEEDBACK_JOB = "class_feedback"
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="learning-job")


def enqueue_student_report(
    db: Session,
    *,
    class_id: int,
    student_id: int,
    requested_by: int,
) -> LearningGenerationJob:
    job, _ = learning_repo.enqueue_learning_job(
        db,
        kind=STUDENT_REPORT_JOB,
        class_id=class_id,
        student_id=student_id,
        requested_by=requested_by,
        dedupe_key=f"student-report:{class_id}:{student_id}",
    )
    if job.status == "queued":
        submit_learning_job(job.id)
    return job


def enqueue_class_feedback(
    db: Session,
    *,
    class_id: int,
    requested_by: int,
) -> LearningGenerationJob:
    job, _ = learning_repo.enqueue_learning_job(
        db,
        kind=CLASS_FEEDBACK_JOB,
        class_id=class_id,
        student_id=None,
        requested_by=requested_by,
        dedupe_key=f"class-feedback:{class_id}",
    )
    if job.status == "queued":
        submit_learning_job(job.id)
    return job


def submit_learning_job(job_id: str) -> None:
    _executor.submit(_run_learning_job, job_id)


def recover_incomplete_learning_jobs() -> int:
    db = SessionLocal()
    try:
        job_ids = learning_repo.recover_learning_jobs(db)
    except Exception:
        logger.exception("恢复学情后台任务失败")
        db.rollback()
        return 0
    finally:
        db.close()
    for job_id in job_ids:
        submit_learning_job(job_id)
    if job_ids:
        logger.info("已恢复学情后台任务 count=%s", len(job_ids))
    return len(job_ids)


def _run_learning_job(job_id: str) -> None:
    started_at = time.perf_counter()
    db = SessionLocal()
    try:
        if not learning_repo.claim_learning_job(db, job_id):
            return
        job = learning_repo.get_learning_job(db, job_id)
        if not job:
            return

        if job.kind == STUDENT_REPORT_JOB:
            if job.student_id is None:
                raise ValueError("学生报告任务缺少学生信息")
            result = generate_student_report_record(
                db,
                job.student_id,
                job.class_id,
                job.requested_by,
                commit=False,
            )
        elif job.kind == CLASS_FEEDBACK_JOB:
            result = generate_class_feedback_record(
                db,
                job.class_id,
                job.requested_by,
                commit=False,
            )
        else:
            raise ValueError("未知的学情任务类型")

        learning_repo.complete_learning_job(db, job, result["id"])
        db.commit()
        logger.info(
            "学情后台任务完成 job_id=%s kind=%s elapsed_ms=%.2f",
            job_id,
            job.kind,
            (time.perf_counter() - started_at) * 1000,
        )
    except Exception as exc:
        db.rollback()
        logger.exception(
            "学情后台任务失败 job_id=%s error_type=%s elapsed_ms=%.2f",
            job_id,
            type(exc).__name__,
            (time.perf_counter() - started_at) * 1000,
        )
        try:
            learning_repo.fail_learning_job(
                db,
                job_id,
                "报告整理失败，请稍后重试",
            )
        except Exception:
            db.rollback()
            logger.exception("保存学情任务失败状态失败 job_id=%s", job_id)
    finally:
        db.close()


def serialize_learning_job(
    db: Session,
    job: LearningGenerationJob,
    *,
    include_result: bool = True,
) -> dict:
    result: Optional[dict] = None
    if include_result and job.status == "completed" and job.result_id is not None:
        if job.kind == STUDENT_REPORT_JOB:
            report = learning_repo.get_student_report(db, job.result_id)
            if report:
                result = _serialize_report(
                    report,
                    learning_repo.get_user_name(db, report.student_id),
                )
        elif job.kind == CLASS_FEEDBACK_JOB:
            feedback = learning_repo.get_class_feedback(db, job.result_id)
            if feedback:
                result = _serialize_feedback(feedback)

    return {
        "id": job.id,
        "kind": job.kind,
        "status": job.status,
        "class_id": job.class_id,
        "student_id": job.student_id,
        "result_id": job.result_id,
        "result": result,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }
