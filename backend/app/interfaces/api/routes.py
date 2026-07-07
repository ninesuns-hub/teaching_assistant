import sys
import os

# 确保可以导入 backend 目录下的模块
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from .schemas import ChatRequest, ChatResponse
from agent_core import ReactAgent
from agent_core.tools import create_admin_tool, create_knowledge_tool
from agent_core.rag import HybridSearcher
from agent_core.config.settings import settings
from database.course_repo import query_course_admin, init_db
from app.core.data_manager import data_manager

# 初始化混合检索器
hybrid_searcher = HybridSearcher()

router = APIRouter()

# 初始化数据库
init_db()

# 使用工厂函数创建工具集
tools = [
    create_admin_tool(query_course_admin),
    create_knowledge_tool(hybrid_searcher.query)
]

# 实例化 ReactAgent
agent = ReactAgent(
    config=settings,
    tools=tools
)

@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        return StreamingResponse(
            agent.stream_chat(request.message),
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset")
async def reset():
    agent.reset()
    return {"message": "对话已重置"}

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    教师上传授课内容接口
    """
    content = await file.read()
    result = data_manager.save_course_file(content, file.filename)
    if result["status"] == "success":
        return {"message": f"文件 {file.filename} 上传并入库成功", "path": result["path"]}
    else:
        raise HTTPException(status_code=500, detail=result["message"])

@router.get("/files")
async def list_files():
    """
    获取已上传文件列表
    """
    return {"files": data_manager.get_all_course_files()}
