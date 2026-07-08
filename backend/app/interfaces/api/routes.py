import sys
import os
import mimetypes

backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from .schemas import ChatRequest
from agent_core import ReactAgent
from agent_core.rag import HybridSearcher
from database.course_repo import query_course_admin, init_db
from database.mysql_db import get_db, User, UserRole
from database import conversation_repo
from agent_core.config.settings import settings
from app.core.data_manager import data_manager
from app.core.chat_image_store import save_chat_image, resolve_image_path
from app.core.agent_bindings import build_agent_tools
from app.core.deps import get_current_user, require_role
from .auth_routes import router as auth_router
from .class_routes import router as class_router
from .conversation_routes import router as conversation_router
from .learning_routes import router as learning_router

hybrid_searcher = HybridSearcher()

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(class_router, prefix="/classes", tags=["classes"])
router.include_router(conversation_router, prefix="/conversations", tags=["conversations"])
router.include_router(learning_router, prefix="/learning", tags=["learning"])

init_db()

_agent_holder: list[ReactAgent | None] = [None]
agent = ReactAgent(
    config=settings,
    tools=build_agent_tools(
        lambda: _agent_holder[0].request_context if _agent_holder[0] else {},
        hybrid_searcher,
        query_course_admin,
    ),
)
_agent_holder[0] = agent


def _build_agent_input(message: str, image_path: Optional[str]) -> str:
    text = message.strip() or "请帮我分析这张图片中的离散数学问题。"
    if image_path:
        return (
            f"{text}\n\n"
            "（学生已上传图片。请先调用 analyze_uploaded_image 工具识图，"
            "必要时再调用 query_lecture_knowledge 检索课件，最后综合回答。）"
        )
    return text


def _stream_and_persist(
    display_message: str,
    agent_input: str,
    conversation_id: int,
    request_context: dict,
    image_path: Optional[str] = None,
):
    from database.mysql_db import SessionLocal

    full_response = ""
    observations = None
    try:
        for chunk in agent.stream_chat(agent_input, request_context=request_context):
            full_response += chunk
            yield chunk
        if hasattr(agent, "last_observations"):
            observations = agent.last_observations
    finally:
        db = SessionLocal()
        try:
            ctx = {}
            if observations:
                ctx["observations"] = observations
            conversation_repo.add_message(
                db,
                conversation_id,
                "user",
                display_message,
                image_path=image_path,
                retrieved_context=ctx if observations else None,
            )
            conversation_repo.add_message(
                db,
                conversation_id,
                "assistant",
                full_response or "（无回复）",
                retrieved_context={"observations": observations} if observations else None,
            )
        finally:
            db.close()


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role is None:
        raise HTTPException(status_code=400, detail="请先选择学生或教师身份")

    conversation = None
    if request.conversation_id:
        conversation = conversation_repo.get_conversation(db, request.conversation_id, current_user.id)
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")

    if not conversation:
        class_id = request.class_id
        if class_id is None and current_user.role == UserRole.STUDENT:
            from database import class_repo
            user_classes = class_repo.get_user_classes(db, current_user)
            if user_classes:
                class_id = user_classes[0]["id"]
        conversation = conversation_repo.create_conversation(db, current_user.id, class_id)

    image_path = None
    if request.image_base64:
        try:
            image_path = save_chat_image(
                current_user.id,
                request.image_base64,
                request.image_mime or "image/jpeg",
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    display_message = request.message.strip() or "[图片]"
    request_context = {"image_path": image_path} if image_path else {}
    agent_input = _build_agent_input(request.message, image_path)

    try:
        return StreamingResponse(
            _stream_and_persist(
                display_message,
                agent_input,
                conversation.id,
                request_context,
                image_path,
            ),
            media_type="text/event-stream",
            headers={"X-Conversation-Id": str(conversation.id)},
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="图片文件不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/images/{user_id}/{filename}")
async def get_chat_image(
    user_id: int,
    filename: str,
    current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="无权访问该图片")
    try:
        path = resolve_image_path(f"{user_id}/{filename}")
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    media_type = mimetypes.guess_type(path)[0] or "image/jpeg"
    return FileResponse(path, media_type=media_type)


@router.post("/reset")
async def reset(current_user: User = Depends(get_current_user)):
    agent.reset()
    return {"message": "对话已重置"}


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(UserRole.TEACHER)),
):
    """兼容旧接口：上传到全局课程目录（建议改用班级资料上传）"""
    content = await file.read()
    result = data_manager.save_course_file(content, file.filename)
    if result["status"] == "success":
        return {"message": f"文件 {file.filename} 上传并入库成功", "path": result["path"]}
    raise HTTPException(status_code=500, detail=result["message"])


@router.get("/files")
async def list_files(current_user: User = Depends(get_current_user)):
    return {"files": data_manager.get_all_course_files()}
