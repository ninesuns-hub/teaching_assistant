from __future__ import annotations

import os
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session

from agent_core.config.settings import settings
from app.core.deps import get_current_user
from app.services.chat_attachment_service import (
    MAX_MESSAGE_ATTACHMENTS,
    MAX_MESSAGE_TOTAL_SIZE,
    AttachmentParseError,
    cleanup_expired_chat_attachments,
    delete_attachment_file,
    office_preview_html,
    resolve_attachment_path,
    safe_filename,
    save_attachment_file,
    serialize_attachment,
    submit_attachment_job,
    validate_document_bytes,
)
from database import chat_attachment_repo
from database.mysql_db import User, get_db


router = APIRouter()


def _content_disposition(filename: str, *, download: bool) -> str:
    disposition = "attachment" if download else "inline"
    fallback = "".join(
        character if character.isascii() and character not in {'"', "\\", "\r", "\n"}
        else "_"
        for character in filename
    ) or "document"
    return (
        f"{disposition}; filename=\"{fallback}\"; "
        f"filename*=UTF-8''{quote(filename, safe='')}"
    )


@router.post("")
async def upload_chat_attachments(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not files or len(files) > MAX_MESSAGE_ATTACHMENTS:
        raise HTTPException(status_code=400, detail="每条消息最多上传 3 个文档")
    cleanup_expired_chat_attachments()
    if (
        chat_attachment_repo.count_recent_uploads(db, current_user.id)
        + len(files)
        > settings.CHAT_ATTACHMENT_UPLOADS_PER_HOUR
    ):
        raise HTTPException(status_code=429, detail="每小时最多上传 20 个文档，请稍后再试")

    validated: list[tuple[str, str, str, bytes]] = []
    total_size = 0
    try:
        for upload in files:
            filename = safe_filename(upload.filename or "document")
            raw = await upload.read()
            total_size += len(raw)
            if total_size > MAX_MESSAGE_TOTAL_SIZE:
                raise AttachmentParseError("单条消息的全部附件合计不能超过 50MB")
            ext, mime_type = validate_document_bytes(filename, raw)
            validated.append((filename, ext, mime_type, raw))
    except AttachmentParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        for upload in files:
            await upload.close()

    created = []
    try:
        for filename, ext, mime_type, raw in validated:
            public_id = str(uuid.uuid4())
            relative_path = save_attachment_file(
                current_user.id,
                public_id,
                ext,
                raw,
            )
            try:
                attachment = chat_attachment_repo.create_attachment(
                    db,
                    public_id=public_id,
                    user_id=current_user.id,
                    filename=filename,
                    file_path=relative_path,
                    file_type=ext.lstrip("."),
                    mime_type=mime_type,
                    file_size=len(raw),
                )
            except Exception:
                delete_attachment_file(relative_path)
                raise
            created.append(attachment)
    except Exception:
        db.rollback()
        for attachment in created:
            delete_attachment_file(attachment.file_path)
            chat_attachment_repo.delete_attachment_record(db, attachment.public_id)
        raise

    for attachment in created:
        submit_attachment_job(attachment.public_id)
    return {"attachments": [serialize_attachment(item) for item in created]}


@router.get("/{public_id}")
def get_chat_attachment(
    public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attachment = chat_attachment_repo.get_owned_attachment(
        db, public_id, current_user.id
    )
    if not attachment:
        raise HTTPException(status_code=404, detail="附件不存在")
    return serialize_attachment(attachment)


@router.delete("/{public_id}")
def delete_chat_attachment(
    public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attachment = chat_attachment_repo.get_owned_attachment(
        db, public_id, current_user.id
    )
    if not attachment:
        raise HTTPException(status_code=404, detail="附件不存在")
    if attachment.message_id is not None:
        raise HTTPException(status_code=409, detail="已发送的附件不能单独删除")
    was_running = attachment.status == "running"
    cancelled = chat_attachment_repo.cancel_unassociated(
        db, public_id, current_user.id
    )
    if not cancelled:
        raise HTTPException(status_code=409, detail="附件当前不能删除")
    if not was_running:
        delete_attachment_file(cancelled.file_path)
        chat_attachment_repo.delete_attachment_record(db, public_id)
    return {"ok": True}


@router.get("/{public_id}/file")
def get_chat_attachment_file(
    public_id: str,
    download: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attachment = chat_attachment_repo.get_owned_attachment(
        db, public_id, current_user.id
    )
    if not attachment:
        raise HTTPException(status_code=404, detail="附件不存在")
    try:
        path = resolve_attachment_path(attachment.file_path)
    except AttachmentParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="附件文件不存在")
    headers = {
        "Content-Disposition": _content_disposition(
            attachment.filename,
            download=download,
        ),
        "X-Content-Type-Options": "nosniff",
    }
    if download:
        return FileResponse(
            path,
            media_type=attachment.mime_type,
            filename=attachment.filename,
            headers=headers,
        )
    if attachment.status != "ready":
        raise HTTPException(status_code=409, detail="附件仍在解析中")
    if attachment.file_type == "pdf":
        return FileResponse(path, media_type="application/pdf", headers=headers)
    response = HTMLResponse(
        office_preview_html(attachment),
        headers=headers,
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'unsafe-inline'; img-src data:"
    )
    return response
