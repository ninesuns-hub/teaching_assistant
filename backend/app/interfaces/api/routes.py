import sys
import os
import mimetypes
import json
import logging
import time
import uuid

backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from .schemas import (
    ChatRequest,
    MermaidRepairCommitRequest,
    MermaidRepairCommitResponse,
    MermaidRepairRequest,
    MermaidRepairResponse,
)
from agent_core import ReactAgent
from database.course_repo import query_course_admin, init_db
from database.mysql_db import get_db, User, UserRole
from database import conversation_repo, rag_repo
from agent_core.config.settings import settings
from app.core.data_manager import data_manager
from app.core.chat_image_store import save_chat_image, resolve_image_path
from app.core.mermaid_service import (
    MermaidSourceConflict,
    repair_mermaid_source,
    replace_saved_mermaid_source,
)
from app.services.learning_jobs import recover_incomplete_learning_jobs
from app.core.agent_bindings import build_agent_tools
from app.core.deps import get_current_user, require_role
from .auth_routes import router as auth_router
from .class_routes import router as class_router
from .conversation_routes import router as conversation_router
from .learning_routes import router as learning_router
from .homework_routes import router as homework_router

hybrid_searcher = data_manager.searcher
logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(class_router, prefix="/classes", tags=["classes"])
router.include_router(conversation_router, prefix="/conversations", tags=["conversations"])
router.include_router(learning_router, prefix="/learning", tags=["learning"])
router.include_router(homework_router, prefix="/homework", tags=["homework"])

init_db()
recover_incomplete_learning_jobs()

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


def _build_welcome_content(
    current_user: User,
    class_name: Optional[str] = None,
    language: str = "zh",
) -> str:
    if language.lower().startswith("en"):
        if current_user.role == UserRole.TEACHER:
            class_context = (
                f" I’m ready to support **{class_name}**."
                if class_name else ""
            )
            return (
                "Hello, teacher! I’m **Xiao Li**, your discrete mathematics "
                f"teaching assistant.{class_context}\n\n"
                "I can help you organize course materials and classes, publish "
                "and review assignments, understand student learning, and answer "
                "common discrete mathematics questions. I’ll keep information "
                "grounded in the selected class and its available materials.\n\n"
                "Choose a class or open a conversation whenever you’re ready."
            )
        class_context = (
            f" We’ll use **{class_name}** as the current course context."
            if class_name else ""
        )
        return (
            "Hello! I’m **Xiao Li**, your discrete mathematics teaching "
            f"assistant 😊{class_context}\n\n"
            "I can explain concepts with clear examples, search course materials, "
            "format mathematics carefully, draw useful diagrams, analyze uploaded "
            "questions, and look up course information.\n\n"
            "Ask me anything about discrete mathematics when you’re ready!"
        )

    if current_user.role == UserRole.TEACHER:
        class_part = (
            f"当前我会以 **{class_name}** 作为班级上下文。"
            if class_name else "选择班级后，我会结合对应班级的数据协助你。"
        )
        return (
            "你好，老师！我是离散数学课程智能助教 **小离**。"
            f"{class_part}\n\n"
            "我可以协助管理课程资料和班级学生、布置并查看作业、整理学情反馈，"
            "也能结合课程资料辅助回答学生常见问题。所有查询和分析都会遵循当前班级"
            "的资料范围，不会虚构尚不存在的数据。\n\n"
            "选择班级或打开一段对话，我们就可以开始了。"
        )

    class_part = (
        f"当前我会结合 **{class_name}** 的课程资料帮助你。"
        if class_name else "加入或选择班级后，我还可以结合对应课程资料回答。"
    )
    return (
        "你好！我是 **小离**，你的离散数学课程智能助教 😊"
        f"{class_part}\n\n"
        "我可以结合课件或通用知识解释集合、逻辑、图论、关系和组合数学等内容，"
        "用清晰的公式、例子和必要的图示帮助理解；你也可以上传题目图片，"
        "或询问老师、评分和课程安排等信息。\n\n"
        "有任何离散数学问题，随时来问我吧！"
    )


def _sse(event_type: str, payload: dict) -> str:
    return (
        f"event: {event_type}\n"
        f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
    )


def _log_chat_timing(request_id: str, stage: str, started_at: float, **fields) -> None:
    logger.info(
        json.dumps(
            {
                "event": "chat_timing",
                "request_id": request_id,
                "stage": stage,
                "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 2),
                **fields,
            },
            ensure_ascii=False,
        )
    )


def _stream_welcome(content: str):
    yield _sse("content", {"delta": content})
    yield _sse("done", {})


def _stream_and_persist(
    display_message: str,
    agent_input: str,
    conversation_id: int,
    conversation_public_id: str,
    request_context: dict,
    image_path: Optional[str] = None,
):
    from database.mysql_db import SessionLocal

    request_id = request_context.get("request_id", "-")
    request_started_at = time.perf_counter()
    full_response = ""
    observations = None
    for event in agent.stream_events(agent_input, request_context=request_context):
        if event["type"] == "content":
            delta = event.get("delta", "")
            if delta:
                full_response += delta
                yield _sse("content", {"delta": delta})
        elif event["type"] == "status":
            yield _sse("status", {"stage": event.get("stage", "understanding")})
        elif event["type"] == "error":
            message = event.get("message", "处理请求时出现错误")
            if not full_response:
                full_response = message
            yield _sse("error", {"message": message})

    if hasattr(agent, "last_observations"):
        observations = agent.last_observations

    save_started_at = time.perf_counter()
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
        assistant_message = conversation_repo.add_message(
            db,
            conversation_id,
            "assistant",
            full_response or "（无回复）",
            retrieved_context={"observations": observations} if observations else None,
        )
    except Exception:
        logger.exception("聊天消息保存失败 request_id=%s", request_id)
        yield _sse("error", {"message": "回答已生成，但保存聊天记录失败"})
        return
    finally:
        db.close()
    _log_chat_timing(request_id, "message_persistence", save_started_at)
    _log_chat_timing(request_id, "request_total", request_started_at)
    yield _sse(
        "done",
        {
            "conversation_id": conversation_public_id,
            "message_id": assistant_message.id,
        },
    )


@router.post("/chat")
def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role is None:
        raise HTTPException(status_code=400, detail="请先选择学生或教师身份")

    from database import class_repo

    conversation = None
    resolved_class_id = None
    if request.conversation_id:
        conversation = conversation_repo.get_conversation(db, request.conversation_id, current_user.id)
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        resolved_class_id = conversation.class_id

    if not conversation:
        resolved_class_id = request.class_id
        if resolved_class_id is not None and not class_repo.user_can_access_class(
            db, current_user, resolved_class_id
        ):
            raise HTTPException(status_code=403, detail="无权使用该班级知识库")
        if resolved_class_id is None and current_user.role == UserRole.STUDENT:
            user_classes = class_repo.get_user_classes(db, current_user)
            if user_classes:
                resolved_class_id = user_classes[0]["id"]
        conversation = conversation_repo.create_conversation(
            db, current_user.id, resolved_class_id
        )
    elif resolved_class_id is not None and not class_repo.user_can_access_class(
        db, current_user, resolved_class_id
    ):
        raise HTTPException(status_code=403, detail="无权使用该班级知识库")

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
    request_context = {
        "user_id": current_user.id,
        "user_role": current_user.role.value,
        "class_id": resolved_class_id,
        "request_id": str(uuid.uuid4()),
    }
    if image_path:
        request_context["image_path"] = image_path
    agent_input = _build_agent_input(request.message, image_path)

    try:
        return StreamingResponse(
            _stream_and_persist(
                display_message,
                agent_input,
                conversation.id,
                conversation.public_id,
                request_context,
                image_path,
            ),
            media_type="text/event-stream",
            headers={
                "X-Conversation-Id": conversation.public_id,
                "X-Chat-Stream-Protocol": "sse-v1",
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="图片文件不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/welcome")
def chat_welcome(
    class_id: Optional[int] = None,
    language: str = "zh",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role is None:
        raise HTTPException(status_code=400, detail="请先选择学生或教师身份")

    from database import class_repo

    class_name = None
    resolved_class_id = class_id
    if resolved_class_id is not None and not class_repo.user_can_access_class(db, current_user, resolved_class_id):
        resolved_class_id = None

    if resolved_class_id is None:
        user_classes = class_repo.get_user_classes(db, current_user)
        if user_classes:
            resolved_class_id = user_classes[0]["id"]
            class_name = user_classes[0]["name"]
    else:
        for item in class_repo.get_user_classes(db, current_user):
            if item["id"] == resolved_class_id:
                class_name = item["name"]
                break

    content = _build_welcome_content(current_user, class_name, language)

    return StreamingResponse(
        _stream_welcome(content),
        media_type="text/event-stream",
        headers={
            "X-Chat-Stream-Protocol": "sse-v1",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/mermaid/repair", response_model=MermaidRepairResponse)
def repair_mermaid(
    payload: MermaidRepairRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message = conversation_repo.get_user_assistant_message(
        db,
        payload.conversation_id,
        payload.message_id,
        current_user.id,
    )
    if not message:
        raise HTTPException(status_code=404, detail="没有找到对应的助手消息")
    try:
        replace_saved_mermaid_source(
            message.content,
            payload.source,
            payload.source,
        )
    except MermaidSourceConflict:
        raise HTTPException(status_code=400, detail="该图表源码不属于对应的助手消息")
    try:
        repaired = repair_mermaid_source(
            payload.source.strip(),
            payload.parse_error,
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Mermaid 修复失败")
        raise HTTPException(status_code=502, detail="图表重新生成失败，请稍后重试") from exc
    return MermaidRepairResponse(source=repaired)


@router.post(
    "/chat/mermaid/repair/commit",
    response_model=MermaidRepairCommitResponse,
)
def commit_mermaid_repair(
    payload: MermaidRepairCommitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message = conversation_repo.get_user_assistant_message_for_update(
        db,
        payload.conversation_id,
        payload.message_id,
        current_user.id,
    )
    if not message:
        raise HTTPException(status_code=404, detail="没有找到对应的助手消息")

    try:
        updated_content, changed = replace_saved_mermaid_source(
            message.content,
            payload.original_source,
            payload.repaired_source,
        )
        if changed:
            message.content = updated_content
            message.conversation.updated_at = conversation_repo.current_utc_time()
        db.commit()
        if changed:
            db.refresh(message)
    except MermaidSourceConflict as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        logger.exception("保存 Mermaid 修复结果失败")
        raise HTTPException(
            status_code=500,
            detail="图表已修复，但保存失败，请重试",
        )

    return MermaidRepairCommitResponse(
        source=payload.repaired_source,
        content=message.content,
    )


@router.get("/chat/images/{user_id}/{filename}")
def get_chat_image(
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
def reset(current_user: User = Depends(get_current_user)):
    agent.reset()
    return {"message": "对话已重置"}


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(UserRole.TEACHER)),
    db: Session = Depends(get_db),
):
    """兼容旧接口：上传到全局课程目录（建议改用班级资料上传）"""
    content = await file.read()
    filename = os.path.basename(file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    result = data_manager.save_course_file(
        content, filename, auto_ingest=False
    )
    if result["status"] != "success":
        raise HTTPException(status_code=500, detail=result["message"])

    content_hash = data_manager.calculate_content_hash(content)
    file_type = os.path.splitext(filename)[1].lower().lstrip(".")
    document, _ = rag_repo.get_or_create_document(
        db,
        content_hash=content_hash,
        file_type=file_type,
        file_size=len(content),
    )
    rag_repo.add_source(
        db,
        document_id=document.id,
        scope_type="global",
        filename=filename,
        file_path=result["path"],
    )
    sources = rag_repo.list_sources(db, document.id)
    scope_keys = rag_repo.scope_keys(sources)
    serialized_sources = rag_repo.serialize_sources(sources)
    reused = document.index_status == "ready"
    if reused:
        data_manager.update_document_access(
            content_hash, scope_keys, serialized_sources
        )
    else:
        indexed = data_manager.ingest_file(
            result["path"],
            metadata={
                "document_hash": content_hash,
                "scope_keys": scope_keys,
                "sources": serialized_sources,
                "source_key": f"document:{content_hash}",
            },
        )
        if not indexed:
            rag_repo.set_document_status(db, document, "failed")
            raise HTTPException(status_code=400, detail="文件中没有可建立索引的文本内容")
        rag_repo.set_document_status(db, document, "ready")
    return {
        "message": (
            f"文件 {filename} 已登记，复用现有内容索引"
            if reused
            else f"文件 {filename} 上传并入库成功"
        ),
        "path": result["path"],
        "content_hash": content_hash,
        "index_reused": reused,
    }


@router.get("/files")
def list_files(current_user: User = Depends(get_current_user)):
    return {"files": data_manager.get_all_course_files()}
