import sys
import os

# 确保可以导入 backend 目录下的模块
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from agent_core.chat_agent import ChatAgent
from app.config.settings import settings
from database.course_repo import query_course_admin, init_db
from database.vector_repo import query as vector_query

def run_cli():
    print("=" * 48)
    print("    离散数学智能助教 (CLI)")
    print("=" * 48)
    print('输入 "exit" 退出，"clear" 重置对话\n')

    # 初始化数据库
    init_db()

    # 实例化 Agent，注入配置和工具
    agent = ChatAgent(
        config=settings,
        admin_query_tool=query_course_admin,
        vector_query_tool=vector_query
    )

    while True:
        try:
            user_input = input("你：").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input: continue
        if user_input.lower() in ["exit", "quit", "退出"]: break
        if user_input.lower() in ["clear", "reset", "清空"]:
            agent.reset()
            print("对话已重置。")
            continue

        try:
            print("助教：思考中...", end="\r")
            reply = agent.chat(user_input)
            print(f"助教：{reply}\n")
        except Exception as e:
            print(f"\n[错误] {e}\n")
