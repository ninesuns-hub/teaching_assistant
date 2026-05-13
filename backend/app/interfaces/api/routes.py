import sys
import os

# 确保可以导入 backend 目录下的模块
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from fastapi import APIRouter, HTTPException
from .schemas import ChatRequest, ChatResponse
from agent_core import ReactAgent
from agent_core.tools import create_admin_tool, create_knowledge_tool
from agent_core.rag import HybridSearcher
from agent_core.config.settings import settings
from database.course_repo import query_course_admin, init_db

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

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        reply = agent.chat(request.message)
        return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset")
async def reset():
    agent.reset()
    return {"message": "对话已重置"}
