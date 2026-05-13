import sys
import os

# 确保可以导入 backend 目录下的模块
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from fastapi import APIRouter, HTTPException
from .schemas import ChatRequest, ChatResponse
from agent_core.chat_agent import ChatAgent
from app.config.settings import settings
from database.course_repo import query_course_admin, init_db
from database.vector_repo import query as vector_query

router = APIRouter()

# 初始化数据库
init_db()

# 实例化 Agent，注入配置和工具
agent = ChatAgent(
    config=settings,
    admin_query_tool=query_course_admin,
    vector_query_tool=vector_query
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
