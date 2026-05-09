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

"""

# 课程事务类，查SQLite
COURSE_ADMIN_KEYWORDS: list[str] = [
    "考试", "期末", "期中", "测验", "quiz", "考试时间", "考试地点", "考试规定",
    "作业", "截止", "提交", "怎么交", "何时交",
    "成绩", "评分", "占比", "平时分", "出勤", "加分", "bonus",
    "上课时间", "上课地点", "教室", "课表", "几点上课",
    "答疑", "office hour", "办公室", "老师", "联系", "邮箱",
    "调课", "放假", "通知", "课程要求", "课堂规定", "政策",
    "学分", "课时", "学时", "先修", "课程编号", "授课语言",
    "参考书", "教材", "textbook", "课程网站", "网站",
    "建议", "学习建议", "课程目标", "教学目标",
]

# 教学内容类，查ChromaDB
COURSE_CONTENT_KEYWORDS: list[str] = [
    "例题", "习题", "讲义", "课件", "ppt", "例",
    "课上", "老师讲", "书上", "教材上", "怎么证明", "证明",
    "定义", "定理", "公式", "运算", "推导", "性质",
    "集合", "图论", "逻辑", "命题", "谓词", "组合", "排列",
    "关系", "函数", "代数", "数论", "群", "环", "域",
    "第0章", "第1章", "第2章", "第3章", "第4章", "第5章",
    "chapter", "slide",
]

# ── 数据库配置────────────────────────────────────────
# 所有数据库文件统一存放在 data/ 目录
DATA_DIR: str         = os.path.join(os.path.dirname(__file__), "data")

# ChromaDB 向量数据库存放路径
VECTOR_DB_PATH: str   = os.path.join(DATA_DIR, "vector_store")

# SQLite 精确信息数据库（阶段3会用到）
SQLITE_DB_PATH: str   = os.path.join(DATA_DIR, "course_info.db")

# 文档切片配置
# 重叠是为了防止一句话被切断后语义丢失
CHUNK_SIZE: int       = 400
CHUNK_OVERLAP: int    = 80

# 向量检索时返回最相关的前 N 个片段
TOP_K: int            = 3