import json
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.mysql_db import (
    StudentLearningReport,
    ClassLearningFeedback,
    LearningGenerationJob,
    User,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def save_student_report(
    db: Session,
    student_id: int,
    class_id: int,
    generated_by: int,
    summary: str,
    stats: dict,
    message_count: int,
    commit: bool = True,
) -> StudentLearningReport:
    report = StudentLearningReport(
        student_id=student_id,
        class_id=class_id,
        generated_by=generated_by,
        summary=summary,
        stats_json=json.dumps(stats, ensure_ascii=False),
        message_count=message_count,
        status="completed",
    )
    db.add(report)
    if commit:
        db.commit()
        db.refresh(report)
    else:
        db.flush()
    return report


def list_student_reports(
    db: Session,
    student_id: int,
    class_id: int,
    limit: int = 20,
) -> List[StudentLearningReport]:
    return (
        db.query(StudentLearningReport)
        .filter(
            StudentLearningReport.student_id == student_id,
            StudentLearningReport.class_id == class_id,
        )
        .order_by(StudentLearningReport.created_at.desc())
        .limit(limit)
        .all()
    )


def get_student_report(db: Session, report_id: int) -> Optional[StudentLearningReport]:
    return db.query(StudentLearningReport).filter(StudentLearningReport.id == report_id).first()


def save_class_feedback(
    db: Session,
    class_id: int,
    teacher_id: int,
    summary: str,
    stats: dict,
    student_count: int,
    commit: bool = True,
) -> ClassLearningFeedback:
    feedback = ClassLearningFeedback(
        class_id=class_id,
        teacher_id=teacher_id,
        summary=summary,
        stats_json=json.dumps(stats, ensure_ascii=False),
        student_count=student_count,
        status="completed",
    )
    db.add(feedback)
    if commit:
        db.commit()
        db.refresh(feedback)
    else:
        db.flush()
    return feedback


def list_class_feedback(db: Session, class_id: int, limit: int = 20) -> List[ClassLearningFeedback]:
    return (
        db.query(ClassLearningFeedback)
        .filter(ClassLearningFeedback.class_id == class_id)
        .order_by(ClassLearningFeedback.created_at.desc())
        .limit(limit)
        .all()
    )


def get_class_feedback(db: Session, feedback_id: int) -> Optional[ClassLearningFeedback]:
    return db.query(ClassLearningFeedback).filter(ClassLearningFeedback.id == feedback_id).first()


def get_user_name(db: Session, user_id: int) -> str:
    user = db.query(User).filter(User.id == user_id).first()
    return user.name if user else f"用户{user_id}"


def enqueue_learning_job(
    db: Session,
    *,
    kind: str,
    class_id: int,
    student_id: Optional[int],
    requested_by: int,
    dedupe_key: str,
) -> tuple[LearningGenerationJob, bool]:
    active = (
        db.query(LearningGenerationJob)
        .filter(LearningGenerationJob.dedupe_key == dedupe_key)
        .first()
    )
    if active:
        return active, False

    job = LearningGenerationJob(
        kind=kind,
        class_id=class_id,
        student_id=student_id,
        requested_by=requested_by,
        status="queued",
        dedupe_key=dedupe_key,
    )
    db.add(job)
    try:
        db.commit()
        db.refresh(job)
        return job, True
    except IntegrityError:
        db.rollback()
        active = (
            db.query(LearningGenerationJob)
            .filter(LearningGenerationJob.dedupe_key == dedupe_key)
            .first()
        )
        if active:
            return active, False
        raise


def get_learning_job(db: Session, job_id: str) -> Optional[LearningGenerationJob]:
    return (
        db.query(LearningGenerationJob)
        .filter(LearningGenerationJob.id == job_id)
        .first()
    )


def get_active_learning_job(
    db: Session,
    *,
    kind: str,
    class_id: int,
    student_id: Optional[int] = None,
) -> Optional[LearningGenerationJob]:
    query = db.query(LearningGenerationJob).filter(
        LearningGenerationJob.kind == kind,
        LearningGenerationJob.class_id == class_id,
        LearningGenerationJob.status.in_(("queued", "running")),
    )
    if student_id is None:
        query = query.filter(LearningGenerationJob.student_id.is_(None))
    else:
        query = query.filter(LearningGenerationJob.student_id == student_id)
    return query.order_by(LearningGenerationJob.created_at.desc()).first()


def claim_learning_job(db: Session, job_id: str) -> bool:
    claimed = (
        db.query(LearningGenerationJob)
        .filter(
            LearningGenerationJob.id == job_id,
            LearningGenerationJob.status == "queued",
        )
        .update(
            {
                LearningGenerationJob.status: "running",
                LearningGenerationJob.started_at: _utc_now(),
                LearningGenerationJob.error_message: None,
            },
            synchronize_session=False,
        )
    )
    db.commit()
    return claimed == 1


def complete_learning_job(
    db: Session,
    job: LearningGenerationJob,
    result_id: int,
) -> None:
    now = _utc_now()
    job.status = "completed"
    job.result_id = result_id
    job.error_message = None
    job.dedupe_key = None
    job.completed_at = now
    job.updated_at = now


def fail_learning_job(
    db: Session,
    job_id: str,
    error_message: str,
) -> None:
    job = get_learning_job(db, job_id)
    if not job:
        return
    now = _utc_now()
    job.status = "failed"
    job.error_message = error_message[:300]
    job.dedupe_key = None
    job.completed_at = now
    job.updated_at = now
    db.commit()


def recover_learning_jobs(db: Session) -> list[str]:
    jobs = (
        db.query(LearningGenerationJob)
        .filter(LearningGenerationJob.status.in_(("queued", "running")))
        .all()
    )
    ids = []
    for job in jobs:
        job.status = "queued"
        job.started_at = None
        job.error_message = None
        ids.append(job.id)
    db.commit()
    return ids
