from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.services.memory_jobs import enqueue_backfill
from database import class_repo, memory_repo, memory_vector_repo
from database.mysql_db import User, get_db
from .schemas import (
    MemoryItemResponse,
    MemoryListResponse,
    MemorySettingsRequest,
    MemorySettingsResponse,
    MemoryUpdateRequest,
)

router = APIRouter()


def _serialize(item) -> MemoryItemResponse:
    return MemoryItemResponse(
        id=item.public_id,
        class_id=item.class_id,
        memory_type=item.memory_type,
        content=item.content,
        confidence=float(item.confidence),
        importance=float(item.importance),
        created_at=item.created_at.isoformat(),
        updated_at=(item.updated_at or item.created_at).isoformat(),
    )


@router.get("/memory/settings", response_model=MemorySettingsResponse)
def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    setting = memory_repo.get_or_create_setting(db, current_user.id)
    return MemorySettingsResponse(
        enabled=setting.enabled,
        backfill_status=setting.backfill_status,
        backfill_processed=setting.backfill_processed,
    )


@router.put("/memory/settings", response_model=MemorySettingsResponse)
def update_settings(
    payload: MemorySettingsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    setting = memory_repo.set_memory_enabled(db, current_user.id, payload.enabled)
    if payload.enabled:
        enqueue_backfill(db, current_user.id)
        db.refresh(setting)
    return MemorySettingsResponse(
        enabled=setting.enabled,
        backfill_status=setting.backfill_status,
        backfill_processed=setting.backfill_processed,
    )


@router.get("/memory", response_model=MemoryListResponse, include_in_schema=False)
@router.get("/memories", response_model=MemoryListResponse)
def list_memories(
    class_id: Optional[int] = Query(None),
    memory_type: Optional[str] = Query(None),
    cursor: Optional[int] = Query(None),
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if class_id is not None and not class_repo.user_can_access_class(db, current_user, class_id):
        raise HTTPException(status_code=403, detail="无权访问该班级记忆")
    if memory_type is not None and memory_type not in memory_repo.ALLOWED_MEMORY_TYPES:
        raise HTTPException(status_code=400, detail="无效的记忆类型")
    items = memory_repo.list_memories(
        db,
        current_user.id,
        class_id=class_id,
        memory_type=memory_type,
        after_id=cursor,
        limit=limit + 1,
    )
    has_more = len(items) > limit
    visible = items[:limit]
    return MemoryListResponse(
        items=[_serialize(item) for item in visible],
        next_cursor=visible[-1].id if has_more and visible else None,
    )


@router.patch(
    "/memory/{memory_id}",
    response_model=MemoryItemResponse,
    include_in_schema=False,
)
@router.patch("/memories/{memory_id}", response_model=MemoryItemResponse)
def update_memory(
    memory_id: str,
    payload: MemoryUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = memory_repo.get_memory(db, current_user.id, memory_id)
    if not item or item.status == "deleted":
        raise HTTPException(status_code=404, detail="记忆不存在")
    try:
        item = memory_repo.update_memory_content(db, item, payload.content)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="相同记忆已经存在")
    try:
        memory_vector_repo.upsert_memory(item)
    except Exception:
        # SQL is the source of truth; vector indexing can recover later.
        pass
    return _serialize(item)


@router.delete("/memory/{memory_id}", include_in_schema=False)
@router.delete("/memories/{memory_id}")
def delete_memory(
    memory_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = memory_repo.get_memory(db, current_user.id, memory_id)
    if not item or item.status == "deleted":
        raise HTTPException(status_code=404, detail="记忆不存在")
    memory_repo.soft_delete_memory(db, item)
    try:
        memory_vector_repo.delete_memory(item.public_id)
    except Exception:
        pass
    return {"ok": True}


@router.delete("/memory", include_in_schema=False)
@router.delete("/memories")
def clear_memories(
    scope: str = Query("all", pattern="^(all|class)$"),
    class_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if scope == "class":
        if class_id is None:
            raise HTTPException(status_code=400, detail="清理班级记忆时必须提供班级")
        if not class_repo.user_can_access_class(db, current_user, class_id):
            raise HTTPException(status_code=403, detail="无权访问该班级记忆")
    public_ids = memory_repo.clear_memories(
        db,
        current_user.id,
        class_id=class_id if scope == "class" else None,
    )
    for public_id in public_ids:
        try:
            memory_vector_repo.delete_memory(public_id)
        except Exception:
            pass
    return {"ok": True, "deleted_count": len(public_ids)}
