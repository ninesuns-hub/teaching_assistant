import mimetypes
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.data_manager import data_manager
from app.core.deps import get_current_user, require_role
from agent_core.config.settings import settings
from database import class_repo, homework_repo
from database.mysql_db import User, UserRole, get_db
from .schemas import HomeworkResponse, HomeworkSubmissionResponse

router = APIRouter()

ALLOWED_EXTS = {".pdf", ".pptx", ".ppsx", ".doc", ".docx", ".zip", ".png", ".jpg", ".jpeg"}


def _parse_due_at(raw: Optional[str]) -> Optional[datetime]:
    if not raw or not raw.strip():
        return None
    text = raw.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.strptime(raw.strip(), "%Y-%m-%dT%H:%M")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="截止日期格式无效") from exc


def _serialize_homework(hw, submission_count: int = 0, my_submission: dict | None = None) -> HomeworkResponse:
    return HomeworkResponse(
        id=hw.id,
        class_id=hw.class_id,
        title=hw.title,
        description=hw.description,
        due_at=hw.due_at.isoformat() if hw.due_at else None,
        attachment_name=hw.attachment_name,
        has_attachment=bool(hw.attachment_path),
        created_at=hw.created_at.isoformat() if hw.created_at else "",
        submission_count=submission_count,
        my_submission=my_submission,
    )


@router.get("/classes/{class_id}/homeworks", response_model=list[HomeworkResponse])
def list_homeworks(
    class_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not class_repo.user_can_access_class(db, current_user, class_id):
        raise HTTPException(status_code=403, detail="无权访问该班级")

    items = homework_repo.list_homeworks(db, class_id)
    result = []
    for hw in items:
        subs = homework_repo.list_submissions(db, hw.id)
        my_sub = None
        if current_user.role == UserRole.STUDENT:
            mine = homework_repo.get_student_submission(db, hw.id, current_user.id)
            if mine:
                my_sub = {
                    "id": mine.id,
                    "content": mine.content,
                    "filename": mine.filename,
                    "has_file": bool(mine.file_path),
                    "submitted_at": mine.submitted_at.isoformat() if mine.submitted_at else None,
                }
        result.append(_serialize_homework(hw, submission_count=len(subs), my_submission=my_sub))
    return result


@router.post("/classes/{class_id}/homeworks", response_model=HomeworkResponse)
async def create_homework(
    class_id: int,
    title: str = Form(...),
    description: str = Form(""),
    due_at: str = Form(""),
    file: UploadFile | None = File(None),
    current_user: User = Depends(require_role(UserRole.TEACHER)),
    db: Session = Depends(get_db),
):
    if not class_repo.user_owns_class(db, current_user, class_id):
        raise HTTPException(status_code=403, detail="仅班级教师可发布作业")
    if not title.strip():
        raise HTTPException(status_code=400, detail="请填写作业标题")

    attachment_path = None
    attachment_name = None
    if file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTS:
            raise HTTPException(status_code=400, detail="不支持的附件格式")
        content = await file.read()
        saved = data_manager.save_homework_file(content, file.filename, class_id, kind="assignment")
        if saved["status"] != "success":
            raise HTTPException(status_code=500, detail=saved.get("message", "附件保存失败"))
        attachment_path = saved["path"]
        attachment_name = file.filename

    hw = homework_repo.create_homework(
        db=db,
        class_id=class_id,
        title=title,
        description=description,
        due_at=_parse_due_at(due_at),
        created_by=current_user.id,
        attachment_path=attachment_path,
        attachment_name=attachment_name,
    )
    return _serialize_homework(hw)


@router.delete("/homeworks/{homework_id}")
def delete_homework(
    homework_id: int,
    current_user: User = Depends(require_role(UserRole.TEACHER)),
    db: Session = Depends(get_db),
):
    hw = homework_repo.get_homework(db, homework_id)
    if not hw:
        raise HTTPException(status_code=404, detail="作业不存在")
    if not class_repo.user_owns_class(db, current_user, hw.class_id):
        raise HTTPException(status_code=403, detail="无权删除该作业")
    homework_repo.delete_homework(db, hw)
    return {"ok": True}


@router.get("/homeworks/{homework_id}/attachment")
def download_homework_attachment(
    homework_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hw = homework_repo.get_homework(db, homework_id)
    if not hw or not hw.attachment_path:
        raise HTTPException(status_code=404, detail="附件不存在")
    if not class_repo.user_can_access_class(db, current_user, hw.class_id):
        raise HTTPException(status_code=403, detail="无权访问")
    if not os.path.isfile(hw.attachment_path):
        raise HTTPException(status_code=404, detail="附件文件缺失")
    return FileResponse(
        hw.attachment_path,
        filename=hw.attachment_name or os.path.basename(hw.attachment_path),
        media_type=mimetypes.guess_type(hw.attachment_path)[0] or "application/octet-stream",
    )


@router.post("/homeworks/{homework_id}/submit", response_model=HomeworkSubmissionResponse)
async def submit_homework(
    homework_id: int,
    content: str = Form(""),
    file: UploadFile | None = File(None),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    hw = homework_repo.get_homework(db, homework_id)
    if not hw:
        raise HTTPException(status_code=404, detail="作业不存在")
    if not class_repo.user_can_access_class(db, current_user, hw.class_id):
        raise HTTPException(status_code=403, detail="无权提交该作业")

    file_path = filename = file_type = None
    file_size = 0
    if file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTS:
            raise HTTPException(status_code=400, detail="不支持的提交文件格式")
        raw = await file.read()
        saved = data_manager.save_homework_file(
            raw,
            file.filename,
            hw.class_id,
            kind="submission",
            homework_id=hw.id,
            student_id=current_user.id,
        )
        if saved["status"] != "success":
            raise HTTPException(status_code=500, detail=saved.get("message", "提交文件保存失败"))
        file_path = saved["path"]
        filename = file.filename
        file_type = ext.lstrip(".")
        file_size = len(raw)

    if not (content or "").strip() and not file_path:
        existing = homework_repo.get_student_submission(db, homework_id, current_user.id)
        if not existing:
            raise HTTPException(status_code=400, detail="请填写文字说明或上传文件")

    sub = homework_repo.upsert_submission(
        db=db,
        homework_id=homework_id,
        student_id=current_user.id,
        content=content,
        file_path=file_path,
        filename=filename,
        file_type=file_type,
        file_size=file_size,
    )
    return HomeworkSubmissionResponse(
        id=sub.id,
        homework_id=sub.homework_id,
        student_id=sub.student_id,
        student_name=current_user.name,
        content=sub.content,
        filename=sub.filename,
        file_type=sub.file_type,
        file_size=sub.file_size or 0,
        has_file=bool(sub.file_path),
        submitted_at=sub.submitted_at.isoformat() if sub.submitted_at else None,
    )


@router.get("/homeworks/{homework_id}/submissions", response_model=list[HomeworkSubmissionResponse])
def list_homework_submissions(
    homework_id: int,
    current_user: User = Depends(require_role(UserRole.TEACHER)),
    db: Session = Depends(get_db),
):
    hw = homework_repo.get_homework(db, homework_id)
    if not hw:
        raise HTTPException(status_code=404, detail="作业不存在")
    if not class_repo.user_owns_class(db, current_user, hw.class_id):
        raise HTTPException(status_code=403, detail="无权查看提交")
    rows = homework_repo.list_submissions(db, homework_id)
    return [HomeworkSubmissionResponse(**row) for row in rows]


@router.get("/submissions/{submission_id}/file")
def download_submission_file(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = homework_repo.get_submission(db, submission_id)
    if not sub or not sub.file_path:
        raise HTTPException(status_code=404, detail="提交文件不存在")
    hw = homework_repo.get_homework(db, sub.homework_id)
    if not hw:
        raise HTTPException(status_code=404, detail="作业不存在")

    is_owner = class_repo.user_owns_class(db, current_user, hw.class_id)
    is_self = current_user.id == sub.student_id
    if not (is_owner or is_self):
        raise HTTPException(status_code=403, detail="无权下载该提交")
    if not os.path.isfile(sub.file_path):
        raise HTTPException(status_code=404, detail="文件缺失")

    return FileResponse(
        sub.file_path,
        filename=sub.filename or os.path.basename(sub.file_path),
        media_type=mimetypes.guess_type(sub.file_path)[0] or "application/octet-stream",
    )
