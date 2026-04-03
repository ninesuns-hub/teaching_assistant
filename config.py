# API Key 系统提示词和全局参数等配置项集中管理，方便后续维护和扩展
import os
from dotenv import load_dotenv

load_dotenv()  # 读取 .env 文件

# ── OpenAI API ─────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://aihubmix.com/v1")
MODEL_NAME: str        = "gpt-4o-free"
MAX_TOKENS: int        = 2048

# ── 系统提示词 ────────────────────────────────────────────────
# 后续阶段可以在这里扩展：告诉 Agent 它有哪些工具可以用
SYSTEM_PROMPT: str = """你是一名离散数学课程的智能助教，名字叫"小离"。

你的职责：
- 耐心解答学生关于离散数学的各种问题
- 解释概念时先给结论，再举例说明，保持简洁清晰
- 如果问题与离散数学无关，礼貌说明并引导回课程话题

当前版本为纯对话模式，后续将支持查询课程数据库和检索课件内容。
"""

# ── 后续阶段扩展区───────────────
# 阶段2：数据库路径
# DB_PATH = "data/course_info.db"

# 阶段2：意图分类关键词
# COURSE_KEYWORDS = ["考试", "作业", "截止", "教室", ...]

# 阶段2：向量数据库路径
# VECTOR_DB_PATH = "data/vector_store"