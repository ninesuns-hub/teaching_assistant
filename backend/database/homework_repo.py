from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from database.mysql_db import (
    HomeworkAssignment,
    HomeworkAttachment,
    HomeworkSubmission,
    HomeworkSubmissionAttachment,
    User,
)


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


def add_attachment(
    db: Session,
    homework_id: int,
    filename: str,
    file_path: str,
    file_type: str,
    file_size: int,
) -> HomeworkAttachment:
    attachment = HomeworkAttachment(
        homework_id=homework_id,
        filename=filename,
        file_path=file_path,
        file_type=file_type,
        file_size=file_size,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def list_attachments(db: Session, homework_id: int) -> List[HomeworkAttachment]:
    return (
        db.query(HomeworkAttachment)
        .filter(HomeworkAttachment.homework_id == homework_id)
        .order_by(HomeworkAttachment.id.asc())
        .all()
    )


def get_attachment(
    db: Session, homework_id: int, attachment_id: int
) -> Optional[HomeworkAttachment]:
    return db.query(HomeworkAttachment).filter(
        HomeworkAttachment.id == attachment_id,
        HomeworkAttachment.homework_id == homework_id,
    ).first()


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


def list_submission_attachments(
    db: Session,
    submission_id: int,
) -> List[HomeworkSubmissionAttachment]:
    return (
        db.query(HomeworkSubmissionAttachment)
        .filter(HomeworkSubmissionAttachment.submission_id == submission_id)
        .order_by(HomeworkSubmissionAttachment.id.asc())
        .all()
    )


def get_submission_attachment(
    db: Session,
    submission_id: int,
    attachment_id: int,
) -> Optional[HomeworkSubmissionAttachment]:
    return (
        db.query(HomeworkSubmissionAttachment)
        .filter(
            HomeworkSubmissionAttachment.id == attachment_id,
            HomeworkSubmissionAttachment.submission_id == submission_id,
        )
        .first()
    )


def save_submission_with_attachments(
    db: Session,
    homework_id: int,
    student_id: int,
    content: Optional[str],
    retained_attachment_ids: set[int],
    new_attachments: list[dict],
) -> tuple[HomeworkSubmission, list[str]]:
    sub = get_student_submission(db, homework_id, student_id)
    if sub is None:
        sub = HomeworkSubmission(
            homework_id=homework_id,
            student_id=student_id,
        )
        db.add(sub)
        db.flush()

    current = list_submission_attachments(db, sub.id)
    removed = [
        attachment
        for attachment in current
        if attachment.id not in retained_attachment_ids
    ]
    retained = [
        attachment
        for attachment in current
        if attachment.id in retained_attachment_ids
    ]
    for attachment in removed:
        db.delete(attachment)

    added = []
    for item in new_attachments:
        attachment = HomeworkSubmissionAttachment(
            submission_id=sub.id,
            filename=item["filename"],
            file_path=item["file_path"],
            file_type=item["file_type"],
            file_size=item["file_size"],
        )
        db.add(attachment)
        added.append(attachment)

    sub.content = (content or "").strip() or None
    sub.submitted_at = datetime.utcnow()
    ordered = retained + added
    first = ordered[0] if ordered else None
    sub.file_path = first.file_path if first else None
    sub.filename = first.filename if first else None
    sub.file_type = first.file_type if first else None
    sub.file_size = first.file_size if first else 0

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(sub)
    return sub, [attachment.file_path for attachment in removed]


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
            "has_file": bool(sub.attachments or sub.file_path),
            "attachments": [
                {
                    "id": attachment.id,
                    "filename": attachment.filename,
                    "file_type": attachment.file_type,
                    "file_size": attachment.file_size or 0,
                }
                for attachment in sub.attachments
            ],
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
        }
        for sub, user in rows
    ]


def get_submission(db: Session, submission_id: int) -> Optional[HomeworkSubmission]:
    return db.query(HomeworkSubmission).filter(HomeworkSubmission.id == submission_id).first()
