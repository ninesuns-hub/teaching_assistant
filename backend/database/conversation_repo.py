import json
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.mysql_db import (
    ChatGenerationLock,
    ChatMessage,
    Conversation,
    ConversationSummary,
    MemoryEvidence,
    MemoryItem,
    MemoryJob,
    User,
)


def create_conversation(
    db: Session,
    user_id: int,
    class_id: Optional[int] = None,
    title: str = "新对话",
) -> Conversation:
    conversation = Conversation(
        public_id=str(uuid.uuid4()),
        user_id=user_id,
        class_id=class_id,
        title=title,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_conversation(db: Session, public_id: str, user_id: int) -> Optional[Conversation]:
    return db.query(Conversation).filter(
        Conversation.public_id == public_id,
        Conversation.user_id == user_id,
    ).first()


def list_user_conversations(db: Session, user_id: int, limit: int = 50) -> List[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
        .all()
    )


def delete_conversation(
    db: Session,
    public_id: str,
    user_id: int,
) -> tuple[bool, list[str]]:
    conversation = get_conversation(db, public_id, user_id)
    if not conversation:
        return False, []
    memory_ids = [
        row[0]
        for row in db.query(MemoryEvidence.memory_id)
        .filter(MemoryEvidence.conversation_id == conversation.id)
        .distinct()
        .all()
    ]
    db.query(MemoryEvidence).filter(
        MemoryEvidence.conversation_id == conversation.id
    ).delete(synchronize_session=False)
    db.query(ChatGenerationLock).filter(
        ChatGenerationLock.conversation_id == conversation.id
    ).delete(synchronize_session=False)
    db.query(MemoryJob).filter(
        MemoryJob.conversation_id == conversation.id
    ).update({"conversation_id": None}, synchronize_session=False)
    db.delete(conversation)
    db.flush()
    for memory_id in memory_ids:
        still_supported = (
            db.query(MemoryEvidence.id)
            .filter(MemoryEvidence.memory_id == memory_id)
            .first()
        )
        if not still_supported:
            db.query(MemoryItem).filter(MemoryItem.id == memory_id).update(
                {"status": "deleted", "updated_at": current_utc_time()},
                synchronize_session=False,
            )
    db.commit()
    deleted_public_ids = (
        [
            row[0]
            for row in db.query(MemoryItem.public_id)
            .filter(
                MemoryItem.id.in_(memory_ids),
                MemoryItem.status == "deleted",
            )
            .all()
        ]
        if memory_ids
        else []
    )
    return True, deleted_public_ids


def rename_conversation(db: Session, public_id: str, user_id: int, title: str) -> Optional[Conversation]:
    conversation = get_conversation(db, public_id, user_id)
    if not conversation:
        return None
    db.query(Conversation).filter(Conversation.id == conversation.id).update(
        {
            Conversation.title: title,
            Conversation.updated_at: conversation.updated_at,
        },
        synchronize_session=False,
    )
    db.commit()
    db.refresh(conversation)
    return conversation


def add_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str,
    retrieved_context: Optional[dict] = None,
    image_path: Optional[str] = None,
    client_message_id: Optional[str] = None,
    in_reply_to_id: Optional[int] = None,
) -> ChatMessage:
    message = ChatMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        image_path=image_path,
        client_message_id=client_message_id,
        in_reply_to_id=in_reply_to_id,
        retrieved_context=json.dumps(retrieved_context, ensure_ascii=False) if retrieved_context else None,
    )
    db.add(message)
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation:
        conversation.updated_at = datetime.utcnow()
        if role == "user" and conversation.title == "新对话":
            title_src = content.strip() or ("[图片]" if image_path else "新对话")
            conversation.title = title_src[:50] + ("..." if len(title_src) > 50 else "")
    db.commit()
    db.refresh(message)
    return message


def list_messages(db: Session, conversation_id: int, limit: int = 200) -> List[ChatMessage]:
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    messages.reverse()
    return messages


def list_recent_messages(
    db: Session,
    conversation_id: int,
    *,
    limit: int = 12,
    before_message_id: Optional[int] = None,
) -> List[ChatMessage]:
    query = db.query(ChatMessage).filter(ChatMessage.conversation_id == conversation_id)
    if before_message_id is not None:
        query = query.filter(ChatMessage.id < before_message_id)
    messages = query.order_by(ChatMessage.id.desc()).limit(limit).all()
    messages.reverse()
    return messages


def get_message_by_client_id(
    db: Session,
    conversation_id: int,
    client_message_id: str,
) -> Optional[ChatMessage]:
    return (
        db.query(ChatMessage)
        .filter(
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.client_message_id == client_message_id,
            ChatMessage.role == "user",
        )
        .first()
    )


def get_reply_for_message(db: Session, user_message_id: int) -> Optional[ChatMessage]:
    return (
        db.query(ChatMessage)
        .filter(
            ChatMessage.in_reply_to_id == user_message_id,
            ChatMessage.role == "assistant",
        )
        .order_by(ChatMessage.id.desc())
        .first()
    )


def acquire_generation_lock(
    db: Session,
    conversation_id: int,
    request_id: str,
    ttl_seconds: int = 1800,
) -> bool:
    now = current_utc_time()
    db.query(ChatGenerationLock).filter(
        ChatGenerationLock.conversation_id == conversation_id,
        ChatGenerationLock.expires_at <= now,
    ).delete(synchronize_session=False)
    db.flush()
    db.add(
        ChatGenerationLock(
            conversation_id=conversation_id,
            request_id=request_id,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
    )
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def release_generation_lock(db: Session, conversation_id: int, request_id: str) -> None:
    db.query(ChatGenerationLock).filter(
        ChatGenerationLock.conversation_id == conversation_id,
        ChatGenerationLock.request_id == request_id,
    ).delete(synchronize_session=False)
    db.commit()


def get_conversation_summary(
    db: Session,
    conversation_id: int,
) -> Optional[ConversationSummary]:
    return (
        db.query(ConversationSummary)
        .filter(ConversationSummary.conversation_id == conversation_id)
        .first()
    )


def upsert_conversation_summary(
    db: Session,
    conversation_id: int,
    summary_text: str,
    state_json: dict,
    summarized_through_message_id: int,
) -> ConversationSummary:
    summary = get_conversation_summary(db, conversation_id)
    if summary is None:
        summary = ConversationSummary(conversation_id=conversation_id)
        db.add(summary)
    summary.summary_text = summary_text
    summary.state_json = json.dumps(state_json, ensure_ascii=False)
    summary.summarized_through_message_id = summarized_through_message_id
    summary.version = (summary.version or 0) + 1
    summary.updated_at = current_utc_time()
    db.flush()
    return summary


def get_user_assistant_message(
    db: Session,
    public_id: str,
    message_id: int,
    user_id: int,
) -> Optional[ChatMessage]:
    conversation = get_conversation(db, public_id, user_id)
    if not conversation:
        return None
    return (
        db.query(ChatMessage)
        .filter(
            ChatMessage.id == message_id,
            ChatMessage.conversation_id == conversation.id,
            ChatMessage.role == "assistant",
        )
        .first()
    )


def get_user_assistant_message_for_update(
    db: Session,
    public_id: str,
    message_id: int,
    user_id: int,
) -> Optional[ChatMessage]:
    return (
        db.query(ChatMessage)
        .join(Conversation, ChatMessage.conversation_id == Conversation.id)
        .filter(
            Conversation.public_id == public_id,
            Conversation.user_id == user_id,
            ChatMessage.id == message_id,
            ChatMessage.role == "assistant",
        )
        .with_for_update()
        .first()
    )


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def update_message_feedback(
    db: Session,
    conversation_id: int,
    message_id: int,
    feedback_type: Optional[str],
) -> Optional[ChatMessage]:
    message = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.id == message_id,
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.role == "assistant",
        )
        .first()
    )
    if not message:
        return None
    message.feedback_type = feedback_type
    message.feedback_at = datetime.utcnow()
    db.commit()
    db.refresh(message)
    return message


def get_student_messages_in_class(
    db: Session,
    student_id: int,
    class_id: int,
    limit: int = 500,
) -> List[dict]:
    """获取学生在某班级上下文下的全部对话消息（扁平列表）"""
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == student_id, Conversation.class_id == class_id)
        .all()
    )
    if not conversations:
        conversations = (
            db.query(Conversation)
            .filter(Conversation.user_id == student_id, Conversation.class_id.is_(None))
            .all()
        )

    conv_ids = [c.id for c in conversations]
    if not conv_ids:
        return []

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id.in_(conv_ids))
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    messages.reverse()
    return [
        {
            "role": m.role,
            "content": m.content,
            "image_path": m.image_path,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


def count_student_messages_in_class(db: Session, student_id: int, class_id: int) -> int:
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == student_id, Conversation.class_id == class_id)
        .all()
    )
    if not conversations:
        conversations = (
            db.query(Conversation)
            .filter(Conversation.user_id == student_id, Conversation.class_id.is_(None))
            .all()
        )
    conv_ids = [c.id for c in conversations]
    if not conv_ids:
        return 0
    return db.query(ChatMessage).filter(ChatMessage.conversation_id.in_(conv_ids)).count()

_TRIVIAL_STUDENT_MESSAGES = {
    "你好", "您好", "嗨", "哈喽", "hello", "hi", "谢谢", "谢谢你", "好的", "好", "收到",
    "再见", "拜拜", "ok", "okay", "test", "测试",
}


def count_effective_student_questions_in_class(db: Session, student_id: int, class_id: int) -> int:
    """Count meaningful student turns for the learning-assistant readiness hint."""
    messages = get_student_messages_in_class(db, student_id, class_id)
    count = 0
    for message in messages:
        if message.get("role") != "user":
            continue
        content = (message.get("content") or "").strip()
        normalized = re.sub(r"[\s\W_]+", "", content.lower(), flags=re.UNICODE)
        if message.get("image_path"):
            count += 1
        elif normalized and normalized not in _TRIVIAL_STUDENT_MESSAGES and len(normalized) >= 3:
            count += 1
    return count
