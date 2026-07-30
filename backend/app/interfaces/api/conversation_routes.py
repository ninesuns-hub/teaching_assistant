import json

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from database.mysql_db import get_db, User
from database import chat_attachment_repo, conversation_repo, memory_vector_repo
from app.core.deps import get_current_user
from app.core.chat_image_store import image_url_for_path
from app.services.chat_attachment_service import (
    delete_attachment_file,
    serialize_attachment,
)
from .schemas import ConversationResponse, ChatMessageResponse, ChatRequest, MessageFeedbackRequest, RenameConversationRequest

router = APIRouter()


def _memory_context_count(raw: str | None) -> int:
    try:
        value = json.loads(raw or "{}")
        return int(value.get("memory_context_count", 0)) if isinstance(value, dict) else 0
    except (TypeError, ValueError, json.JSONDecodeError):
        return 0


@router.get("", response_model=list[ConversationResponse])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversations = conversation_repo.list_user_conversations(db, current_user.id)
    return [
        ConversationResponse(
            id=c.public_id,
            title=c.title,
            class_id=c.class_id,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat() if c.updated_at else c.created_at.isoformat(),
        )
        for c in conversations
    ]


@router.post("", response_model=ConversationResponse)
def create_conversation(
    class_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = conversation_repo.create_conversation(db, current_user.id, class_id)
    return ConversationResponse(
        id=conversation.public_id,
        title=conversation.title,
        class_id=conversation.class_id,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat() if conversation.updated_at else conversation.created_at.isoformat(),
    )


@router.get("/{public_id}/messages", response_model=list[ChatMessageResponse])
def get_conversation_messages(
    public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = conversation_repo.get_conversation(db, public_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    messages = conversation_repo.list_messages(db, conversation.id)
    attachments_by_message = chat_attachment_repo.list_for_message_ids(
        db, [message.id for message in messages]
    )
    return [
        ChatMessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            image_url=image_url_for_path(m.image_path),
            attachments=[
                serialize_attachment(item)
                for item in attachments_by_message.get(m.id, [])
            ],
            feedback=m.feedback_type,
            memory_context_count=_memory_context_count(m.retrieved_context)
            if m.role == "assistant" else 0,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]


@router.post("/{public_id}/messages/{message_id}/feedback")
def set_message_feedback(
    public_id: str,
    message_id: int,
    payload: MessageFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = conversation_repo.get_conversation(db, public_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    if payload.feedback_type not in {"positive", "negative", None}:
        raise HTTPException(status_code=400, detail="无效的反馈类型")

    message = conversation_repo.update_message_feedback(db, conversation.id, message_id, payload.feedback_type)
    if not message:
        raise HTTPException(status_code=404, detail="没有可反馈的助手消息")

    return {"ok": True, "feedback_type": message.feedback_type}


@router.patch("/{public_id}", response_model=ConversationResponse)
def rename_conversation(
    public_id: str,
    payload: RenameConversationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = conversation_repo.rename_conversation(db, public_id, current_user.id, payload.title)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    return ConversationResponse(
        id=conversation.public_id,
        title=conversation.title,
        class_id=conversation.class_id,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat() if conversation.updated_at else conversation.created_at.isoformat(),
    )


@router.delete("/{public_id}")
def delete_conversation(
    public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = conversation_repo.get_conversation(
        db, public_id, current_user.id
    )
    attachment_paths = (
        chat_attachment_repo.list_paths_for_conversation(db, conversation.id)
        if conversation
        else []
    )
    deleted, memory_ids = conversation_repo.delete_conversation(
        db, public_id, current_user.id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="会话不存在")
    for memory_id in memory_ids:
        try:
            memory_vector_repo.delete_memory(memory_id)
        except Exception:
            pass
    for path in attachment_paths:
        delete_attachment_file(path)
    return {"ok": True}
