import logging
from .mysql_db import SessionLocal, CourseInfo, init_mysql
from sqlalchemy import or_

logger = logging.getLogger(__name__)

def init_db() -> None:
    """初始化 MySQL 数据库并写入示例数据"""
    logger.info("初始化 MySQL 数据库...")
    init_mysql()
    
    db = SessionLocal()
    try:
        count = db.query(CourseInfo).count()
        if count == 0:
            from .sample_data import SAMPLE_COURSE_DATA
            for cat, kws, ques, ans in SAMPLE_COURSE_DATA:
                course = CourseInfo(
                    category=cat,
                    keywords=kws,
                    question=ques,
                    answer=ans
                )
                db.add(course)
            db.commit()
            logger.info(f"[MySQL] 课程数据初始化完成，共写入 {len(SAMPLE_COURSE_DATA)} 条记录")
    except Exception as e:
        logger.error(f"初始化数据库失败: {e}")
        db.rollback()
    finally:
        db.close()

def query_course_admin(query_str: str) -> str | None:
    """
    查询课程行政信息。
    支持按类别(category)精准查询或按关键词(keywords)模糊查询。
    """
    db = SessionLocal()
    query_str = query_str.lower().strip()
    
    try:
        # 获取所有数据进行内存匹配（保持与原有逻辑一致的权重排序）
        rows = db.query(CourseInfo.category, CourseInfo.keywords, CourseInfo.answer).all()
        
        matched = []
        for category, keywords_str, answer in rows:
            # 1. 尝试类别精准匹配
            if query_str == category.lower():
                matched.append((100, len(category), answer))
                continue

            # 2. 尝试关键词匹配
            keywords = [kw.strip().lower() for kw in keywords_str.split(",")]
            hit_count = sum(1 for kw in keywords if kw and (kw in query_str or query_str in kw))
            if hit_count > 0:
                max_kw_len = max([len(kw) for kw in keywords if kw and (kw in query_str or query_str in kw)] or [0])
                matched.append((hit_count, max_kw_len, answer))

        if not matched:
            return None

        matched.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return "\n\n---\n\n".join(item[2] for item in matched)
    except Exception as e:
        logger.error(f"查询数据库失败: {e}")
        return None
    finally:
        db.close()
