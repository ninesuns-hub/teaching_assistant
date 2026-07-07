import sqlite3
import os
import logging
from agent_core.config.settings import settings

logger = logging.getLogger(__name__)

def init_db() -> None:
    os.makedirs(os.path.dirname(settings.SQLITE_DB_PATH), exist_ok=True)
    logger.info(f"初始化 SQLite 数据库: {settings.SQLITE_DB_PATH}")
    conn = sqlite3.connect(settings.SQLITE_DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS course_info (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            category    TEXT NOT NULL,
            keywords    TEXT NOT NULL,
            question    TEXT NOT NULL,
            answer      TEXT NOT NULL,
            updated_at  TEXT DEFAULT (date('now'))
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM course_info")
    if cursor.fetchone()[0] == 0:
        from .sample_data import SAMPLE_COURSE_DATA
        cursor.executemany(
            "INSERT INTO course_info (category, keywords, question, answer) VALUES (?, ?, ?, ?)",
            SAMPLE_COURSE_DATA
        )
        logger.info(f"[SQLite] 课程数据初始化完成，共写入 {len(SAMPLE_COURSE_DATA)} 条记录")

    conn.commit()
    conn.close()


def query_course_admin(query_str: str) -> str | None:
    """
    查询课程行政信息。
    支持按类别(category)精准查询或按关键词(keywords)模糊查询。
    """
    conn = sqlite3.connect(settings.SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT category, keywords, answer FROM course_info")
    rows = cursor.fetchall()
    conn.close()

    query_str = query_str.lower().strip()
    matched = []

    for category, keywords_str, answer in rows:
        # 1. 尝试类别精准匹配
        if query_str == category.lower():
            matched.append((100, len(category), answer)) # 类别匹配给予最高权重
            continue

        # 2. 尝试关键词匹配
        keywords = [kw.strip().lower() for kw in keywords_str.split(",")]
        # 只要关键词在查询串中，或者查询串在关键词中（模糊匹配）
        hit_count = sum(1 for kw in keywords if kw and (kw in query_str or query_str in kw))
        if hit_count > 0:
            max_kw_len = max([len(kw) for kw in keywords if kw and (kw in query_str or query_str in kw)] or [0])
            matched.append((hit_count, max_kw_len, answer))

    if not matched:
        return None

    # 按权重排序：类别匹配优先，其次是关键词命中数，最后是匹配长度
    matched.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return "\n\n---\n\n".join(item[2] for item in matched)
