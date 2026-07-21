import json
from typing import Optional

from sqlalchemy.orm import Session

from database import class_repo, conversation_repo, learning_repo
from database.mysql_db import ClassRoom, User
from agent_core.skills import generate_student_report, generate_class_feedback


def generate_student_report_record(
    db: Session,
    student_id: int,
    class_id: int,
    generated_by: int,
) -> dict:
    classroom = db.query(ClassRoom).filter(ClassRoom.id == class_id).first()
    if not classroom:
        raise ValueError("班级不存在")

    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise ValueError("学生不存在")

    messages = conversation_repo.get_student_messages_in_class(db, student_id, class_id)
    result = generate_student_report(student.name, classroom.name, messages)

    report = learning_repo.save_student_report(
        db=db,
        student_id=student_id,
        class_id=class_id,
        generated_by=generated_by,
        summary=result["summary"],
        stats=result.get("stats", {}),
        message_count=len(messages),
    )
    return _serialize_report(report, student.name)


def generate_class_feedback_record(
    db: Session,
    class_id: int,
    teacher_id: int,
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
    feedback = learning_repo.save_class_feedback(
        db=db,
        class_id=class_id,
        teacher_id=teacher_id,
        summary=result["summary"],
        stats=result.get("stats", {}),
        student_count=len(students),
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
