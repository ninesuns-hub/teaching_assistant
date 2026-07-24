"""组装 Agent 工具链：注入后端数据访问能力"""
from typing import Callable, List
from agent_core.tools import (
    create_admin_tool,
    create_knowledge_tool,
    create_image_understanding_tool,
    create_student_report_tool,
    create_class_feedback_tool,
)
from agent_core.skills import generate_student_report, generate_class_feedback
from typing import Callable, List

from sqlalchemy.orm import Session

from agent_core.rag import HybridSearcher
from database import class_repo, conversation_repo, learning_repo
from database.mysql_db import ClassRoom, User


def _student_report_handler(db: Session, generated_by: int) -> Callable[[int, int], str]:
    def handler(student_id: int, class_id: int) -> str:
        classroom = db.query(ClassRoom).filter(ClassRoom.id == class_id).first()
        student = db.query(User).filter(User.id == student_id).first()
        if not classroom or not student:
            return "学生或班级不存在。"

        messages = conversation_repo.get_student_messages_in_class(db, student_id, class_id)
        result = generate_student_report(student.name, classroom.name, messages)
        learning_repo.save_student_report(
            db=db,
            student_id=student_id,
            class_id=class_id,
            generated_by=generated_by,
            summary=result["summary"],
            stats=result.get("stats", {}),
            message_count=len(messages),
        )
        return result["summary"]

    return handler


def _class_feedback_handler(db: Session, teacher_id: int) -> Callable[[int], str]:
    def handler(class_id: int) -> str:
        classroom = db.query(ClassRoom).filter(ClassRoom.id == class_id).first()
        if not classroom:
            return "班级不存在。"

        students = class_repo.list_class_students(db, class_id)
        student_reports = []
        message_stats = []

        for s in students:
            msg_count = conversation_repo.count_student_messages_in_class(db, s["id"], class_id)
            message_stats.append({"student_name": s["name"], "message_count": msg_count})
            reports = learning_repo.list_student_reports(db, s["id"], class_id, limit=1)
            if reports:
                student_reports.append({
                    "student_name": s["name"],
                    "summary_excerpt": reports[0].summary[:1000],
                })
            elif msg_count > 0:
                quick = generate_student_report(
                    s["name"],
                    classroom.name,
                    conversation_repo.get_student_messages_in_class(db, s["id"], class_id),
                )
                student_reports.append({
                    "student_name": s["name"],
                    "summary_excerpt": quick["summary"][:1000],
                })

        result = generate_class_feedback(classroom.name, student_reports, message_stats)
        learning_repo.save_class_feedback(
            db=db,
            class_id=class_id,
            teacher_id=teacher_id,
            summary=result["summary"],
            stats=result.get("stats", {}),
            student_count=len(students),
        )
        return result["summary"]

    return handler


def build_agent_tools(
    context_getter: Callable[[], dict],
    hybrid_searcher: HybridSearcher,
    query_course_admin,
    db: Session | None = None,
    generated_by: int | None = None,
    include_learning_tools: bool = False,
) -> List:
    tools = [
        create_admin_tool(query_course_admin),
        create_knowledge_tool(hybrid_searcher.query, context_getter),
        create_image_understanding_tool(context_getter),
    ]
    if include_learning_tools and db is not None and generated_by is not None:
        tools.append(create_student_report_tool(_student_report_handler(db, generated_by)))
        tools.append(create_class_feedback_tool(_class_feedback_handler(db, generated_by)))
    return tools
