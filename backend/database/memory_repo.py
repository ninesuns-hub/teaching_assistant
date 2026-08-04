import re
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.mysql_db import (
    ChatMessage,
    Conversation,
    MemoryEvidence,
    MemoryItem,
    MemoryJob,
    UserMemorySetting,
    utc_now,
)


ALLOWED_MEMORY_TYPES = {
    "communication_preference",
    "learning_preference",
    "course_learning_state",
    "explicit_user_fact",
    "unresolved_learning_goal",
}


def normalize_key(content: str) -> str:
    normalized = re.sub(r"\s+", " ", content.casefold()).strip()
    return normalized[:255]


def get_or_create_setting(db: Session, user_id: int) -> UserMemorySetting:
    setting = db.query(UserMemorySetting).filter(UserMemorySetting.user_id == user_id).first()
    if setting is None:
        setting = UserMemorySetting(user_id=user_id, enabled=False)
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting


def set_memory_enabled(db: Session, user_id: int, enabled: bool) -> UserMemorySetting:
    setting = get_or_create_setting(db, user_id)
    setting.enabled = enabled
    if enabled and setting.backfill_status in {"not_started", "failed", "cancelled"}:
        setting.backfill_status = "queued"
    elif not enabled and setting.backfill_status in {"queued", "running"}:
        setting.backfill_status = "cancelled"
    setting.updated_at = utc_now()
    db.commit()
    db.refresh(setting)
    return setting


def list_memories(
    db: Session,
    user_id: int,
    *,
    class_id: Optional[int] = None,
    memory_type: Optional[str] = None,
    after_id: Optional[int] = None,
    limit: int = 50,
) -> list[MemoryItem]:
    query = db.query(MemoryItem).filter(
        MemoryItem.user_id == user_id,
        MemoryItem.status == "active",
    )
    if class_id is not None:
        query = query.filter(MemoryItem.class_id == class_id)
    if memory_type is not None:
        query = query.filter(MemoryItem.memory_type == memory_type)
    if after_id is not None:
        query = query.filter(MemoryItem.id < after_id)
    return query.order_by(MemoryItem.id.desc()).limit(limit).all()


def get_memory(db: Session, user_id: int, public_id: str) -> Optional[MemoryItem]:
    return db.query(MemoryItem).filter(
        MemoryItem.public_id == public_id,
        MemoryItem.user_id == user_id,
    ).first()


def upsert_memory(
    db: Session,
    *,
    user_id: int,
    class_id: Optional[int],
    memory_type: str,
    content: str,
    confidence: float,
    importance: float,
    conversation_id: int,
    message_id: int,
    evidence_excerpt: str,
    normalized_key: Optional[str] = None,
) -> tuple[MemoryItem, bool]:
    if memory_type not in ALLOWED_MEMORY_TYPES:
        raise ValueError("unsupported memory type")
    key = normalize_key(normalized_key or content)
    memory = db.query(MemoryItem).filter(
        MemoryItem.user_id == user_id,
        MemoryItem.class_id == class_id,
        MemoryItem.memory_type == memory_type,
        MemoryItem.normalized_key == key,
    ).first()
    created = memory is None
    if memory is None:
        memory = MemoryItem(
            public_id=str(uuid.uuid4()),
            user_id=user_id,
            class_id=class_id,
            memory_type=memory_type,
            content=content.strip(),
            normalized_key=key,
            confidence=max(0.0, min(1.0, confidence)),
            importance=max(0.0, min(1.0, importance)),
        )
        db.add(memory)
        db.flush()
    else:
        if memory.content != content.strip():
            memory.content = content.strip()
            memory.version = (memory.version or 0) + 1
        memory.status = "active"
        memory.confidence = max(memory.confidence or 0, confidence)
        memory.importance = max(memory.importance or 0, importance)
        memory.updated_at = utc_now()
    evidence = db.query(MemoryEvidence).filter(
        MemoryEvidence.memory_id == memory.id,
        MemoryEvidence.message_id == message_id,
    ).first()
    if evidence is None:
        db.add(MemoryEvidence(
            memory_id=memory.id,
            conversation_id=conversation_id,
            message_id=message_id,
            evidence_excerpt=evidence_excerpt[:500],
        ))
    db.flush()
    return memory, created


def update_memory_content(
    db: Session,
    memory: MemoryItem,
    content: str,
) -> MemoryItem:
    memory.content = content.strip()
    memory.normalized_key = normalize_key(content)
    memory.version = (memory.version or 0) + 1
    memory.updated_at = utc_now()
    db.commit()
    db.refresh(memory)
    return memory


def soft_delete_memory(db: Session, memory: MemoryItem) -> None:
    memory.status = "deleted"
    memory.updated_at = utc_now()
    db.commit()


def clear_memories(db: Session, user_id: int, class_id: Optional[int] = None) -> list[str]:
    query = db.query(MemoryItem).filter(
        MemoryItem.user_id == user_id,
        MemoryItem.status != "deleted",
    )
    if class_id is not None:
        query = query.filter(MemoryItem.class_id == class_id)
    items = query.all()
    public_ids = [item.public_id for item in items]
    for item in items:
        item.status = "deleted"
        item.updated_at = utc_now()
    db.commit()
    return public_ids


def recent_relevant_memories(
    db: Session,
    user_id: int,
    class_id: Optional[int],
    limit: int = 5,
) -> list[MemoryItem]:
    now = utc_now()
    query = db.query(MemoryItem).filter(
        MemoryItem.user_id == user_id,
        MemoryItem.status == "active",
        ((MemoryItem.expires_at.is_(None)) | (MemoryItem.expires_at > now)),
    )
    if class_id is None:
        query = query.filter(MemoryItem.class_id.is_(None))
    else:
        query = query.filter(
            (MemoryItem.class_id.is_(None)) | (MemoryItem.class_id == class_id)
        )
    return query.order_by(
        MemoryItem.importance.desc(),
        MemoryItem.updated_at.desc(),
    ).limit(limit).all()


def enqueue_job(
    db: Session,
    *,
    kind: str,
    user_id: int,
    conversation_id: Optional[int],
    dedupe_key: str,
) -> MemoryJob:
    existing = db.query(MemoryJob).filter(MemoryJob.dedupe_key == dedupe_key).first()
    if existing:
        return existing
    job = MemoryJob(
        id=str(uuid.uuid4()),
        kind=kind,
        user_id=user_id,
        conversation_id=conversation_id,
        dedupe_key=dedupe_key,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return db.query(MemoryJob).filter(MemoryJob.dedupe_key == dedupe_key).first()
    db.refresh(job)
    return job


def claim_job(db: Session, job_id: str) -> bool:
    updated = db.query(MemoryJob).filter(
        MemoryJob.id == job_id,
        MemoryJob.status == "queued",
    ).update(
        {"status": "running", "started_at": utc_now(), "error_message": None},
        synchronize_session=False,
    )
    db.commit()
    return bool(updated)


def recover_jobs(db: Session) -> list[str]:
    jobs = db.query(MemoryJob).filter(MemoryJob.status.in_(("queued", "running"))).all()
    for job in jobs:
        job.status = "queued"
        job.started_at = None
    db.commit()
    return [job.id for job in jobs]


def complete_job(db: Session, job: MemoryJob) -> None:
    job.status = "completed"
    job.completed_at = utc_now()
    job.updated_at = utc_now()
    db.commit()


def fail_job(db: Session, job_id: str, message: str) -> None:
    db.query(MemoryJob).filter(MemoryJob.id == job_id).update(
        {
            "status": "failed",
            "error_message": message[:300],
            "completed_at": utc_now(),
            "updated_at": utc_now(),
        },
        synchronize_session=False,
    )
    db.commit()


def all_user_messages_after(
    db: Session,
    user_id: int,
    after_id: int,
    limit: int = 100,
) -> list[ChatMessage]:
    from database import conversation_repo

    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.id.asc())
        .all()
    )
    messages = [
        message
        for conversation in conversations
        for message in conversation_repo.list_messages(db, conversation.id, limit=10000)
        if message.role == "user" and message.id > after_id
    ]
    messages.sort(key=lambda message: message.id)
    return messages[:limit]
