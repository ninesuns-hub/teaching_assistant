import json
from typing import List, Optional

from sqlalchemy.orm import Session

from database.mysql_db import StudentLearningReport, ClassLearningFeedback, User


def save_student_report(
    db: Session,
    student_id: int,
    class_id: int,
    generated_by: int,
    summary: str,
    stats: dict,
    message_count: int,
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
    db.commit()
    db.refresh(report)
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
    db.commit()
    db.refresh(feedback)
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
