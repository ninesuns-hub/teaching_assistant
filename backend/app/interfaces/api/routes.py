from fastapi import APIRouter, HTTPException
from .schemas import ChatRequest, ChatResponse
from app.core.agent import ChatAgent

router = APIRouter()
agent = ChatAgent()

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
