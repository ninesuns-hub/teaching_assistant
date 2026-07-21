import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from app.interfaces.api.routes import router as chat_router
from app.utils.logger import setup_logger
import uvicorn

# 初始化全局日志
setup_logger()
logger = logging.getLogger(__name__)

app = FastAPI(title="Discrete Math Tutor API")


@app.exception_handler(SQLAlchemyError)
async def handle_database_error(request: Request, exc: SQLAlchemyError):
    logger.exception("数据库请求失败: %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "服务暂时不可用，请稍后再试"},
    )

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Conversation-Id"],
)

# 注册路由
app.include_router(chat_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
