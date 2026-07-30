from __future__ import annotations

from datetime import timedelta
from typing import Iterable, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.mysql_db import ChatMessage, ChatMessageAttachment, utc_now


def create_attachment(
    db: Session,
    *,
    public_id: str,
    user_id: int,
    filename: str,
    file_path: str,
    file_type: str,
    mime_type: str,
    file_size: int,
) -> ChatMessageAttachment:
    attachment = ChatMessageAttachment(
        public_id=public_id,
        user_id=user_id,
        filename=filename,
        file_path=file_path,
        file_type=file_type,
        mime_type=mime_type,
        file_size=file_size,
        status="queued",
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def get_owned_attachment(
    db: Session,
    public_id: str,
    user_id: int,
) -> Optional[ChatMessageAttachment]:
    return (
        db.query(ChatMessageAttachment)
        .filter(
            ChatMessageAttachment.public_id == public_id,
            ChatMessageAttachment.user_id == user_id,
        )
        .first()
    )


def get_attachment(db: Session, public_id: str) -> Optional[ChatMessageAttachment]:
    return (
        db.query(ChatMessageAttachment)
        .filter(ChatMessageAttachment.public_id == public_id)
        .first()
    )


def count_recent_uploads(db: Session, user_id: int, *, hours: int = 1) -> int:
    cutoff = utc_now() - timedelta(hours=hours)
    return (
        db.query(func.count(ChatMessageAttachment.id))
        .filter(
            ChatMessageAttachment.user_id == user_id,
            ChatMessageAttachment.created_at >= cutoff,
            ChatMessageAttachment.status != "cancelled",
        )
        .scalar()
        or 0
    )


def count_recent_ocr_documents(db: Session, user_id: int, *, hours: int = 1) -> int:
    cutoff = utc_now() - timedelta(hours=hours)
    return (
        db.query(func.count(ChatMessageAttachment.id))
        .filter(
            ChatMessageAttachment.user_id == user_id,
            ChatMessageAttachment.created_at >= cutoff,
            ChatMessageAttachment.requires_ocr.is_(True),
            ChatMessageAttachment.status != "cancelled",
        )
        .scalar()
        or 0
    )


def claim_attachment(db: Session, public_id: str) -> bool:
    updated = (
        db.query(ChatMessageAttachment)
        .filter(
            ChatMessageAttachment.public_id == public_id,
            ChatMessageAttachment.status == "queued",
        )
        .update(
            {
                ChatMessageAttachment.status: "running",
                ChatMessageAttachment.error_message: None,
                ChatMessageAttachment.updated_at: utc_now(),
            },
            synchronize_session=False,
        )
    )
    db.commit()
    return updated == 1


def is_cancelled(db: Session, public_id: str) -> bool:
    status = (
        db.query(ChatMessageAttachment.status)
        .filter(ChatMessageAttachment.public_id == public_id)
        .scalar()
    )
    return status in {None, "cancelled"}


def update_progress(
    db: Session,
    public_id: str,
    *,
    current: int,
    total: int,
    requires_ocr: Optional[bool] = None,
) -> None:
    values = {
        ChatMessageAttachment.progress_current: current,
        ChatMessageAttachment.progress_total: total,
        ChatMessageAttachment.updated_at: utc_now(),
    }
    if requires_ocr is not None:
        values[ChatMessageAttachment.requires_ocr] = requires_ocr
    db.query(ChatMessageAttachment).filter(
        ChatMessageAttachment.public_id == public_id,
        ChatMessageAttachment.status == "running",
    ).update(values, synchronize_session=False)
    db.commit()


def complete_attachment(
    db: Session,
    public_id: str,
    *,
    extracted_content: list[dict],
    truncated: bool,
) -> None:
    db.query(ChatMessageAttachment).filter(
        ChatMessageAttachment.public_id == public_id,
        ChatMessageAttachment.status == "running",
    ).update(
        {
            ChatMessageAttachment.status: "ready",
            ChatMessageAttachment.extracted_content: extracted_content,
            ChatMessageAttachment.extraction_truncated: truncated,
            ChatMessageAttachment.error_message: None,
            ChatMessageAttachment.updated_at: utc_now(),
        },
        synchronize_session=False,
    )
    db.commit()


def fail_attachment(db: Session, public_id: str, message: str) -> None:
    db.query(ChatMessageAttachment).filter(
        ChatMessageAttachment.public_id == public_id,
        ChatMessageAttachment.status.in_(("queued", "running")),
    ).update(
        {
            ChatMessageAttachment.status: "failed",
            ChatMessageAttachment.error_message: message[:500],
            ChatMessageAttachment.updated_at: utc_now(),
        },
        synchronize_session=False,
    )
    db.commit()


def recover_incomplete(db: Session) -> list[str]:
    attachments = (
        db.query(ChatMessageAttachment)
        .filter(ChatMessageAttachment.status.in_(("queued", "running")))
        .all()
    )
    ids = [item.public_id for item in attachments]
    for item in attachments:
        item.status = "queued"
        item.progress_current = 0
        item.error_message = None
        item.updated_at = utc_now()
    db.commit()
    return ids


def cancel_unassociated(
    db: Session,
    public_id: str,
    user_id: int,
) -> Optional[ChatMessageAttachment]:
    attachment = get_owned_attachment(db, public_id, user_id)
    if not attachment or attachment.message_id is not None:
        return None
    attachment.status = "cancelled"
    attachment.updated_at = utc_now()
    db.commit()
    db.refresh(attachment)
    return attachment


def delete_attachment_record(db: Session, public_id: str) -> None:
    db.query(ChatMessageAttachment).filter(
        ChatMessageAttachment.public_id == public_id
    ).delete(synchronize_session=False)
    db.commit()


def expired_unassociated(
    db: Session,
    *,
    retention_hours: int,
    limit: int = 100,
) -> list[ChatMessageAttachment]:
    cutoff = utc_now() - timedelta(hours=retention_hours)
    return (
        db.query(ChatMessageAttachment)
        .filter(
            ChatMessageAttachment.message_id.is_(None),
            ChatMessageAttachment.created_at < cutoff,
            ChatMessageAttachment.status != "running",
        )
        .order_by(ChatMessageAttachment.created_at.asc())
        .limit(limit)
        .all()
    )


def list_owned_for_send(
    db: Session,
    public_ids: Iterable[str],
    user_id: int,
) -> list[ChatMessageAttachment]:
    ids = list(dict.fromkeys(public_ids))
    if not ids:
        return []
    rows = (
        db.query(ChatMessageAttachment)
        .filter(
            ChatMessageAttachment.public_id.in_(ids),
            ChatMessageAttachment.user_id == user_id,
        )
        .all()
    )
    by_id = {row.public_id: row for row in rows}
    return [by_id[item] for item in ids if item in by_id]


def attach_to_message(
    db: Session,
    attachments: Iterable[ChatMessageAttachment],
    message_id: int,
) -> None:
    for attachment in attachments:
        attachment.message_id = message_id
        attachment.updated_at = utc_now()
    db.flush()


def list_for_message_ids(
    db: Session,
    message_ids: Iterable[int],
) -> dict[int, list[ChatMessageAttachment]]:
    ids = list(message_ids)
    result: dict[int, list[ChatMessageAttachment]] = {item: [] for item in ids}
    if not ids:
        return result
    rows = (
        db.query(ChatMessageAttachment)
        .filter(ChatMessageAttachment.message_id.in_(ids))
        .order_by(ChatMessageAttachment.id.asc())
        .all()
    )
    for row in rows:
        if row.message_id is not None:
            result.setdefault(row.message_id, []).append(row)
    return result


def list_ready_for_conversation(
    db: Session,
    conversation_id: int,
) -> list[ChatMessageAttachment]:
    return (
        db.query(ChatMessageAttachment)
        .join(ChatMessage, ChatMessage.id == ChatMessageAttachment.message_id)
        .filter(
            ChatMessage.conversation_id == conversation_id,
            ChatMessageAttachment.status == "ready",
        )
        .order_by(ChatMessageAttachment.message_id.desc(), ChatMessageAttachment.id.asc())
        .all()
    )


def list_paths_for_conversation(db: Session, conversation_id: int) -> list[str]:
    return [
        row[0]
        for row in (
            db.query(ChatMessageAttachment.file_path)
            .join(ChatMessage, ChatMessage.id == ChatMessageAttachment.message_id)
            .filter(ChatMessage.conversation_id == conversation_id)
            .all()
        )
    ]
