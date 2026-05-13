import sqlite3
import os
from app.config.settings import settings


def init_db() -> None:
    os.makedirs(os.path.dirname(settings.SQLITE_DB_PATH), exist_ok=True)
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
        print(f"[SQLite] 课程数据初始化完成，共写入 {len(SAMPLE_COURSE_DATA)} 条记录")

    conn.commit()
    conn.close()


def query_course_admin(user_question: str) -> str | None:
    conn = sqlite3.connect(settings.SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT keywords, answer FROM course_info")
    rows = cursor.fetchall()
    conn.close()

    matched = []
    for keywords_str, answer in rows:
        keywords = [kw.strip() for kw in keywords_str.split(",")]
        hit_count = sum(1 for kw in keywords if kw and kw in user_question)
        max_kw_len = max([len(kw) for kw in keywords if kw and kw in user_question] or [0])

        if hit_count > 0:
            matched.append((hit_count, max_kw_len, answer))

    if not matched:
        return None

    matched.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return "\n\n---\n\n".join(item[2] for item in matched)
