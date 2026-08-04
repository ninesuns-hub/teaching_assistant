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
    commit: bool = True,
) -> ChatMessage:
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if in_reply_to_id is None and conversation and conversation.active_leaf_message_id:
        in_reply_to_id = conversation.active_leaf_message_id
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
    if conversation:
        conversation.updated_at = datetime.utcnow()
        if role == "user" and conversation.title == "新对话":
            title_src = content.strip() or ("[图片]" if image_path else "新对话")
            conversation.title = title_src[:50] + ("..." if len(title_src) > 50 else "")
    db.flush()
    if conversation:
        conversation.active_leaf_message_id = message.id
    if commit:
        db.commit()
        db.refresh(message)
    return message


def _message_map(db: Session, conversation_id: int) -> dict[int, ChatMessage]:
    return {
        message.id: message
        for message in db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.id.asc())
        .all()
    }


def message_path(
    db: Session,
    conversation_id: int,
    leaf_message_id: Optional[int],
) -> List[ChatMessage]:
    if leaf_message_id is None:
        return []
    by_id = _message_map(db, conversation_id)
    path: list[ChatMessage] = []
    seen: set[int] = set()
    current = by_id.get(leaf_message_id)
    while current is not None and current.id not in seen:
        seen.add(current.id)
        path.append(current)
        current = by_id.get(current.in_reply_to_id)
    path.reverse()
    return path


def list_messages(db: Session, conversation_id: int, limit: int = 200) -> List[ChatMessage]:
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        return []
    leaf_id = conversation.active_leaf_message_id
    if leaf_id is None:
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(limit)
            .all()
        )
        messages.reverse()
        return messages
    messages = message_path(db, conversation_id, leaf_id)
    return messages[-limit:]


def list_recent_messages(
    db: Session,
    conversation_id: int,
    *,
    limit: int = 12,
    before_message_id: Optional[int] = None,
) -> List[ChatMessage]:
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        return []
    leaf_id = before_message_id or conversation.active_leaf_message_id
    messages = message_path(db, conversation_id, leaf_id)
    if before_message_id is not None and messages and messages[-1].id == before_message_id:
        messages = messages[:-1]
    return messages[-limit:]


def set_active_leaf(
    db: Session,
    conversation_id: int,
    message_id: Optional[int],
    *,
    commit: bool = True,
) -> None:
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        return
    conversation.active_leaf_message_id = message_id
    conversation.updated_at = datetime.utcnow()
    if commit:
        db.commit()
    else:
        db.flush()


def get_message(
    db: Session,
    conversation_id: int,
    message_id: int,
) -> Optional[ChatMessage]:
    return db.query(ChatMessage).filter(
        ChatMessage.id == message_id,
        ChatMessage.conversation_id == conversation_id,
    ).first()


def list_answer_variants(db: Session, user_message_id: int) -> List[ChatMessage]:
    return (
        db.query(ChatMessage)
        .filter(
            ChatMessage.in_reply_to_id == user_message_id,
            ChatMessage.role == "assistant",
        )
        .order_by(ChatMessage.id.asc())
        .all()
    )


def answer_variant_metadata(db: Session, messages: List[ChatMessage]) -> dict[int, dict]:
    parent_ids = {message.in_reply_to_id for message in messages if message.role == "assistant"}
    result: dict[int, dict] = {}
    for parent_id in parent_ids:
        if parent_id is None:
            continue
        variants = list_answer_variants(db, parent_id)
        for index, variant in enumerate(variants):
            result[variant.id] = {
                "variant_index": index + 1,
                "variant_count": len(variants),
                "previous_variant_id": variants[index - 1].id if index > 0 else None,
                "next_variant_id": variants[index + 1].id if index + 1 < len(variants) else None,
                "can_retry": len(variants) < 5,
            }
    return result


def newest_descendant_leaf(
    db: Session,
    conversation_id: int,
    root_message_id: int,
) -> Optional[int]:
    by_id = _message_map(db, conversation_id)
    if root_message_id not in by_id:
        return None
    children: dict[int, list[int]] = {}
    for message in by_id.values():
        if message.in_reply_to_id is not None:
            children.setdefault(message.in_reply_to_id, []).append(message.id)
    leaves: list[int] = []
    stack = [root_message_id]
    seen: set[int] = set()
    while stack:
        message_id = stack.pop()
        if message_id in seen:
            continue
        seen.add(message_id)
        descendants = children.get(message_id, [])
        if descendants:
            stack.extend(descendants)
        else:
            leaves.append(message_id)
    return max(leaves or [root_message_id])


def is_message_on_active_path(
    db: Session,
    conversation_id: int,
    message_id: Optional[int],
) -> bool:
    if message_id is None:
        return False
    return any(
        message.id == message_id
        for message in list_messages(db, conversation_id, limit=10000)
    )


def is_message_in_ancestry(
    db: Session,
    conversation_id: int,
    leaf_message_id: int,
    candidate_message_id: Optional[int],
) -> bool:
    if candidate_message_id is None:
        return False
    return any(
        message.id == candidate_message_id
        for message in message_path(db, conversation_id, leaf_message_id)
    )


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

    messages = []
    for conversation in conversations:
        messages.extend(list_messages(db, conversation.id, limit=limit))
    messages.sort(key=lambda item: (item.created_at or datetime.min, item.id))
    messages = messages[-limit:]
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
    return sum(len(list_messages(db, conversation.id, limit=10000)) for conversation in conversations)

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
