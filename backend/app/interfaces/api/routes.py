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


def _build_welcome_input(current_user: User, class_name: Optional[str] = None) -> str:
    if current_user.role == UserRole.TEACHER:
        class_part = f"当前教师正在管理的班级是“{class_name}”。" if class_name else "当前教师还没有选定班级。"
        return (
            "请你以离散数学课程智能助教“小离”的身份，向已经登录的教师做一段自然、完整的自我介绍。"
            f"{class_part}"
            "介绍中要说明你可以帮助教师进行课程资料管理、班级学生管理、作业与提交查看、学情分析，以及辅助回答学生常见问题，不用全部涉及。"
            "语气要专业、温和、简洁但不要敷衍，长度控制在 2 到 4 个自然段，开头和结尾保持简洁清晰简单引入、收束即可，不要过于冗长。"
            "分点阐述但不超过5点，介绍过程中不要重复，可以加上类似“😊”这样的表情但不要太多（一两个即可）。"
            "不要提到这是系统触发的介绍，不要说你没有权限，也不要虚构还不存在的数据。"
        )

    class_part = f"你当前服务的课程班级是“{class_name}”。" if class_name else "当前学生已经登录，但还没有明确课程班级上下文。"
    return (
        "请你以离散数学课程智能助教“小离”的身份，向已经登录的学生做一段自我介绍。"
        f"{class_part}"
        "介绍中要说明你可以实现的功能，必要时可以分点阐述，不超过5个能力点，介绍能力时不要出现类似于“📚”的小图标。"
        "禁止展示 Markdown、LaTeX、Mermaid 的具体语法、定界符或代码示例，只允许自然语言描述排版能力。"
        "语气要像课程助教一样亲切、可靠、有一点鼓励感，内容清晰不要冗长，长度控制在2 到 4 个自然段。"
        "在介绍开头和结尾段可以出现类似于“😊”这样的表情，但不要一样。"
        "不要提到这是系统触发的介绍，不要要求用户重新登录。"
        "可以参考下面示例的结构与语言，但不要照搬示例内容：\n"
        "【参考示例】\n"
        "你好！我是**小离**，你的离散数学课程智能助教 😊\n\n"
        "我的职责包括：\n\n"
        "- 耐心解答你关于离散数学的各种问题"
        "（集合论、逻辑、图论、代数结构、组合数学等）。\n"
        "- 基于课程课件或通用知识，用简洁、清晰的方式解释概念，"
        "先给结论再举例。\n"
        "- 支持 Markdown 排版、LaTeX 数学公式、Mermaid 图形"
        "（如 Hasse 图、树、图等）。\n"
        "- 如果你上传图片，我也会尽量读取并帮助分析。\n"
        "- 如果有课程行政问题（老师、评分、课表等），"
        "我也可以查询相关信息。\n"
        "- 如果问题与离散数学无关，我会礼貌地引导回课程话题。\n\n"
        "有任何离散数学的问题，尽管问我吧！\n\n"
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


def _stream_welcome(agent_input: str, request_context: dict):
    for event in agent.stream_events(agent_input, request_context=request_context):
        if event["type"] == "content":
            yield _sse("content", {"delta": event.get("delta", "")})
        elif event["type"] == "status":
            yield _sse("status", {"stage": event.get("stage", "understanding")})
        elif event["type"] == "error":
            yield _sse("error", {"message": event.get("message", "生成介绍失败")})
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

    request_context = {
        "welcome": True,
        "user_id": current_user.id,
        "user_role": current_user.role.value,
        "class_id": resolved_class_id,
        "request_id": str(uuid.uuid4()),
    }
    agent_input = _build_welcome_input(current_user, class_name)

    return StreamingResponse(
        _stream_welcome(agent_input, request_context),
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
