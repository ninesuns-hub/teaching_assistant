from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from database.mysql_db import HomeworkAssignment, HomeworkSubmission, User


def create_homework(
    db: Session,
    class_id: int,
    title: str,
    description: Optional[str],
    due_at: Optional[datetime],
    created_by: int,
    attachment_path: Optional[str] = None,
    attachment_name: Optional[str] = None,
) -> HomeworkAssignment:
    hw = HomeworkAssignment(
        class_id=class_id,
        title=title.strip(),
        description=(description or "").strip() or None,
        due_at=due_at,
        created_by=created_by,
        attachment_path=attachment_path,
        attachment_name=attachment_name,
    )
    db.add(hw)
    db.commit()
    db.refresh(hw)
    return hw


def get_homework(db: Session, homework_id: int) -> Optional[HomeworkAssignment]:
    return db.query(HomeworkAssignment).filter(HomeworkAssignment.id == homework_id).first()


def list_homeworks(db: Session, class_id: int) -> List[HomeworkAssignment]:
    return (
        db.query(HomeworkAssignment)
        .filter(HomeworkAssignment.class_id == class_id)
        .order_by(HomeworkAssignment.created_at.desc())
        .all()
    )


def delete_homework(db: Session, homework: HomeworkAssignment) -> None:
    db.delete(homework)
    db.commit()


def upsert_submission(
    db: Session,
    homework_id: int,
    student_id: int,
    content: Optional[str],
    file_path: Optional[str],
    filename: Optional[str],
    file_type: Optional[str],
    file_size: int = 0,
) -> HomeworkSubmission:
    sub = (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.homework_id == homework_id,
            HomeworkSubmission.student_id == student_id,
        )
        .first()
    )
    if sub:
        if content is not None:
            sub.content = content.strip() or None
        if file_path:
            sub.file_path = file_path
            sub.filename = filename
            sub.file_type = file_type
            sub.file_size = file_size
        sub.submitted_at = datetime.utcnow()
    else:
        sub = HomeworkSubmission(
            homework_id=homework_id,
            student_id=student_id,
            content=(content or "").strip() or None,
            file_path=file_path,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
        )
        db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def get_student_submission(
    db: Session, homework_id: int, student_id: int
) -> Optional[HomeworkSubmission]:
    return (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.homework_id == homework_id,
            HomeworkSubmission.student_id == student_id,
        )
        .first()
    )


def list_submissions(db: Session, homework_id: int) -> List[dict]:
    rows = (
        db.query(HomeworkSubmission, User)
        .join(User, User.id == HomeworkSubmission.student_id)
        .filter(HomeworkSubmission.homework_id == homework_id)
        .order_by(HomeworkSubmission.submitted_at.desc())
        .all()
    )
    return [
        {
            "id": sub.id,
            "homework_id": sub.homework_id,
            "student_id": sub.student_id,
            "student_name": user.name,
            "content": sub.content,
            "filename": sub.filename,
            "file_type": sub.file_type,
            "file_size": sub.file_size or 0,
            "has_file": bool(sub.file_path),
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
        }
        for sub, user in rows
    ]


def get_submission(db: Session, submission_id: int) -> Optional[HomeworkSubmission]:
    return db.query(HomeworkSubmission).filter(HomeworkSubmission.id == submission_id).first()
