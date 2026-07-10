import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from database.mysql_db import Conversation, ChatMessage, User


def create_conversation(
    db: Session,
    user_id: int,
    class_id: Optional[int] = None,
    title: str = "新对话",
) -> Conversation:
    conversation = Conversation(user_id=user_id, class_id=class_id, title=title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_conversation(db: Session, conversation_id: int, user_id: int) -> Optional[Conversation]:
    return db.query(Conversation).filter(
        Conversation.id == conversation_id,
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


def delete_conversation(db: Session, conversation_id: int, user_id: int) -> bool:
    conversation = get_conversation(db, conversation_id, user_id)
    if not conversation:
        return False
    db.delete(conversation)
    db.commit()
    return True


def add_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str,
    retrieved_context: Optional[dict] = None,
    image_path: Optional[str] = None,
) -> ChatMessage:
    message = ChatMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        image_path=image_path,
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
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
        .all()
    )


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
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
        .all()
    )
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
