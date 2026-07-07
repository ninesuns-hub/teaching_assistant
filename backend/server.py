from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.interfaces.api.routes import router as chat_router
from app.utils.logger import setup_logger
import uvicorn

# 初始化全局日志
setup_logger()

app = FastAPI(title="Discrete Math Tutor API")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
