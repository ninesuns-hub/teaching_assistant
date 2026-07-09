import json

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from database.mysql_db import get_db, User
from database import conversation_repo
from app.core.deps import get_current_user
from app.core.chat_image_store import image_url_for_path
from .schemas import ConversationResponse, ChatMessageResponse, ChatRequest

router = APIRouter()


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversations = conversation_repo.list_user_conversations(db, current_user.id)
    return [
        ConversationResponse(
            id=c.id,
            title=c.title,
            class_id=c.class_id,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat() if c.updated_at else c.created_at.isoformat(),
        )
        for c in conversations
    ]


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    class_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = conversation_repo.create_conversation(db, current_user.id, class_id)
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        class_id=conversation.class_id,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat() if conversation.updated_at else conversation.created_at.isoformat(),
    )


@router.get("/{conversation_id}/messages", response_model=list[ChatMessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = conversation_repo.get_conversation(db, conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    messages = conversation_repo.list_messages(db, conversation_id)
    return [
        ChatMessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            image_url=image_url_for_path(m.image_path),
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted = conversation_repo.delete_conversation(db, conversation_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True}
