from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

class Settings(BaseSettings):
    # ── OpenAI API 配置 ──
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://aihubmix.com/v1"
    MODEL_NAME: str = "gpt-4o-free"
    EMBEDDING_MODEL_NAME: str = "text-embedding-3-small"
    MAX_TOKENS: int = 2048
    
    # ── 系统提示词 ──
    SYSTEM_PROMPT: str = """你是一名离散数学课程的智能助教，名字叫"小离"。
你的职责：
- 耐心解答学生关于离散数学的各种问题
- 解释概念时先给结论，再举例说明，保持简洁清晰
- 如果问题与离散数学无关，礼貌说明并引导回课程话题
"""

    # ── 业务关键词配置 ──
    COURSE_ADMIN_KEYWORDS: List[str] = [
        "考试", "期末", "期中", "测验", "quiz", "考试时间", "考试地点", "考试规定",
        "作业", "截止", "提交", "怎么交", "何时交", "成绩", "评分", "占比", "平时分",
        "出勤", "加分", "bonus", "上课时间", "上课地点", "教室", "课表", "几点上课",
        "答疑", "office hour", "办公室", "老师", "联系", "邮箱", "调课", "放假",
        "通知", "课程要求", "课堂规定", "政策", "学分", "课时", "学时", "先修",
        "课程编号", "授课语言", "参考书", "教材", "textbook", "课程网站", "网站",
        "建议", "学习建议", "课程目标", "教学目标"
    ]
    
    COURSE_CONTENT_KEYWORDS: List[str] = [
        "例题", "习题", "讲义", "课件", "ppt", "例", "课上", "老师讲", "书上",
        "教材上", "怎么证明", "证明", "定义", "定理", "公式", "运算", "推导",
        "性质", "集合", "图论", "逻辑", "命题", "谓词", "组合", "排列", "关系",
        "函数", "代数", "数论", "群", "环", "域", "第0章", "第1章", "第2章",
        "第3章", "第4章", "第5章", "chapter", "slide"
    ]

    # ── 数据库路径配置 ──
    # 默认数据根目录
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    
    VECTOR_DB_PATH: str = os.path.join(DATA_DIR, "vector_store")
    SQLITE_DB_PATH: str = os.path.join(DATA_DIR, "course_info.db")

    # ── 检索配置 ──
    CHUNK_SIZE: int = 400
    CHUNK_OVERLAP: int = 80
    TOP_K: int = 3
    SIMILARITY_THRESHOLD: float = 0.3

    # ── Pydantic Settings 配置 ──
    # 自动读取 .env 文件，支持热修改（重启生效）
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# 全局单例配置对象
settings = Settings()
