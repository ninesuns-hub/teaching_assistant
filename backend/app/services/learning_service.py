import json
from typing import Optional

from sqlalchemy.orm import Session

from database import class_repo, conversation_repo, learning_repo
from database.mysql_db import ClassRoom, User
from agent_core.skills import generate_student_report, generate_class_feedback

REPORT_INPUT_CHAR_LIMIT = 60_000


def _bound_report_messages(messages: list[dict]) -> tuple[list[dict], bool]:
    """Keep the newest complete messages within the report prompt budget."""
    selected = []
    used = 0
    content_trimmed = False
    for message in reversed(messages):
        size = len(message.get("content") or "") + 32
        if selected and used + size > REPORT_INPUT_CHAR_LIMIT:
            break
        if not selected and size > REPORT_INPUT_CHAR_LIMIT:
            message = {
                **message,
                "content": (message.get("content") or "")[-REPORT_INPUT_CHAR_LIMIT:],
            }
            size = REPORT_INPUT_CHAR_LIMIT
            content_trimmed = True
        selected.append(message)
        used += size
    selected.reverse()
    return selected, content_trimmed or len(selected) < len(messages)


def generate_student_report_record(
    db: Session,
    student_id: int,
    class_id: int,
    generated_by: int,
    commit: bool = True,
) -> dict:
    classroom = db.query(ClassRoom).filter(ClassRoom.id == class_id).first()
    if not classroom:
        raise ValueError("班级不存在")

    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise ValueError("学生不存在")

    total_message_count = conversation_repo.count_student_messages_in_class(
        db, student_id, class_id
    )
    messages = conversation_repo.get_student_messages_in_class(
        db, student_id, class_id, limit=500
    )
    analyzed_messages, truncated = _bound_report_messages(messages)
    result = generate_student_report(student.name, classroom.name, analyzed_messages)
    stats = result.get("stats", {})
    stats.update({
        "message_count": total_message_count,
        "total_message_count": total_message_count,
        "analyzed_message_count": len(analyzed_messages),
        "input_truncated": truncated or total_message_count > len(messages),
    })

    report = learning_repo.save_student_report(
        db=db,
        student_id=student_id,
        class_id=class_id,
        generated_by=generated_by,
        summary=result["summary"],
        stats=stats,
        message_count=total_message_count,
        commit=commit,
    )
    return _serialize_report(report, student.name)


def generate_class_feedback_record(
    db: Session,
    class_id: int,
    teacher_id: int,
    commit: bool = True,
) -> dict:
    classroom = db.query(ClassRoom).filter(ClassRoom.id == class_id).first()
    if not classroom:
        raise ValueError("班级不存在")

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
            messages = conversation_repo.get_student_messages_in_class(
                db, s["id"], class_id, limit=500
            )
            analyzed_messages, _ = _bound_report_messages(messages)
            quick = generate_student_report(
                s["name"],
                classroom.name,
                analyzed_messages,
            )
            student_reports.append({
                "student_name": s["name"],
                "summary_excerpt": quick["summary"][:1000],
            })

    result = generate_class_feedback(classroom.name, student_reports, message_stats)
    feedback = learning_repo.save_class_feedback(
        db=db,
        class_id=class_id,
        teacher_id=teacher_id,
        summary=result["summary"],
        stats=result.get("stats", {}),
        student_count=len(students),
        commit=commit,
    )
    return _serialize_feedback(feedback)


def _serialize_report(report, student_name: Optional[str] = None) -> dict:
    stats = {}
    if report.stats_json:
        try:
            stats = json.loads(report.stats_json)
        except json.JSONDecodeError:
            stats = {}
    return {
        "id": report.id,
        "student_id": report.student_id,
        "student_name": student_name,
        "class_id": report.class_id,
        "summary": report.summary,
        "stats": stats,
        "message_count": report.message_count,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


def _serialize_feedback(feedback) -> dict:
    stats = {}
    if feedback.stats_json:
        try:
            stats = json.loads(feedback.stats_json)
        except json.JSONDecodeError:
            stats = {}
    return {
        "id": feedback.id,
        "class_id": feedback.class_id,
        "summary": feedback.summary,
        "stats": stats,
        "student_count": feedback.student_count,
        "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
    }
