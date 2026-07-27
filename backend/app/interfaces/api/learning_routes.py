from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session

from database.mysql_db import get_db, User, UserRole
from database import class_repo, conversation_repo, learning_repo
from app.core.deps import get_current_user, require_role
from app.services.learning_service import (
    _serialize_report,
    _serialize_feedback,
)
from app.services.learning_jobs import (
    CLASS_FEEDBACK_JOB,
    STUDENT_REPORT_JOB,
    enqueue_class_feedback,
    enqueue_student_report,
    serialize_learning_job,
)
from .schemas import (
    AddStudentRequest,
    ClassFeedbackResponse,
    LearningGenerationJobResponse,
    LearningReportResponse,
    StudentBriefResponse,
)

router = APIRouter()


def _ensure_teacher_class_access(db: Session, user: User, class_id: int):
    if not class_repo.user_owns_class(db, user, class_id):
        raise HTTPException(status_code=403, detail="无权访问该班级")


@router.get("/classes/{class_id}/students", response_model=list[StudentBriefResponse])
def list_class_students(
    class_id: int,
    current_user: User = Depends(require_role(UserRole.TEACHER)),
    db: Session = Depends(get_db),
):
    _ensure_teacher_class_access(db, current_user, class_id)
    students = class_repo.list_class_students(db, class_id)
    return [
        StudentBriefResponse(
            id=s["id"],
            name=s["name"],
            email=s["email"],
            joined_at=s["joined_at"],
            message_count=conversation_repo.count_student_messages_in_class(db, s["id"], class_id),
            effective_question_count=conversation_repo.count_effective_student_questions_in_class(
                db, s["id"], class_id
            ),
        )
        for s in students
    ]


@router.post("/classes/{class_id}/students", response_model=StudentBriefResponse)
def add_class_student(
    class_id: int,
    payload: AddStudentRequest,
    current_user: User = Depends(require_role(UserRole.TEACHER)),
    db: Session = Depends(get_db),
):
    _ensure_teacher_class_access(db, current_user, class_id)
    email = (payload.email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="邮箱不能为空")

    student = db.query(User).filter(User.email == email).first()
    if not student:
        raise HTTPException(status_code=404, detail="未找到该用户")
    if student.role != UserRole.STUDENT:
        raise HTTPException(status_code=400, detail="该用户不是学生")

    member = class_repo.add_student_to_class(db, class_id, student.id)
    return StudentBriefResponse(
        id=student.id,
        name=student.name,
        email=student.email,
        joined_at=member.joined_at.isoformat() if member.joined_at else None,
        message_count=conversation_repo.count_student_messages_in_class(db, student.id, class_id),
        effective_question_count=conversation_repo.count_effective_student_questions_in_class(
            db, student.id, class_id
        ),
    )


@router.delete("/classes/{class_id}/students/{student_id}")
def remove_class_student(
    class_id: int,
    student_id: int,
    current_user: User = Depends(require_role(UserRole.TEACHER)),
    db: Session = Depends(get_db),
):
    _ensure_teacher_class_access(db, current_user, class_id)
    removed = class_repo.remove_student_from_class(db, class_id, student_id)
    if not removed:
        raise HTTPException(status_code=404, detail="学生不在该班级中")
    return {"ok": True}


@router.post(
    "/classes/{class_id}/students/{student_id}/report",
    response_model=LearningGenerationJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_student_report(
    class_id: int,
    student_id: int,
    current_user: User = Depends(require_role(UserRole.TEACHER)),
    db: Session = Depends(get_db),
):
    _ensure_teacher_class_access(db, current_user, class_id)
    member_ids = {s["id"] for s in class_repo.list_class_students(db, class_id)}
    if student_id not in member_ids:
        raise HTTPException(status_code=400, detail="该学生不在本班级中")
    job = enqueue_student_report(
        db,
        class_id=class_id,
        student_id=student_id,
        requested_by=current_user.id,
    )
    return serialize_learning_job(db, job, include_result=False)


@router.get("/classes/{class_id}/students/{student_id}/reports", response_model=list[LearningReportResponse])
def list_student_reports(
    class_id: int,
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == UserRole.TEACHER:
        _ensure_teacher_class_access(db, current_user, class_id)
    elif current_user.role == UserRole.STUDENT:
        if current_user.id != student_id:
            raise HTTPException(status_code=403, detail="无权查看他人学情报告")
        if not class_repo.user_can_access_class(db, current_user, class_id):
            raise HTTPException(status_code=403, detail="无权访问该班级")
    else:
        raise HTTPException(status_code=400, detail="请先选择身份")

    student_name = learning_repo.get_user_name(db, student_id)
    reports = learning_repo.list_student_reports(db, student_id, class_id)
    return [_serialize_report(r, student_name) for r in reports]


@router.get("/reports/{report_id}", response_model=LearningReportResponse)
def get_report_detail(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = learning_repo.get_student_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    if current_user.role == UserRole.STUDENT and current_user.id != report.student_id:
        raise HTTPException(status_code=403, detail="无权查看该报告")
    if current_user.role == UserRole.TEACHER and not class_repo.user_owns_class(db, current_user, report.class_id):
        raise HTTPException(status_code=403, detail="无权查看该报告")

    student_name = learning_repo.get_user_name(db, report.student_id)
    return _serialize_report(report, student_name)


@router.post(
    "/classes/{class_id}/feedback",
    response_model=LearningGenerationJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_class_feedback(
    class_id: int,
    current_user: User = Depends(require_role(UserRole.TEACHER)),
    db: Session = Depends(get_db),
):
    _ensure_teacher_class_access(db, current_user, class_id)
    job = enqueue_class_feedback(
        db,
        class_id=class_id,
        requested_by=current_user.id,
    )
    return serialize_learning_job(db, job, include_result=False)


@router.get("/classes/{class_id}/feedback", response_model=list[ClassFeedbackResponse])
def list_class_feedback(
    class_id: int,
    current_user: User = Depends(require_role(UserRole.TEACHER)),
    db: Session = Depends(get_db),
):
    _ensure_teacher_class_access(db, current_user, class_id)
    feedbacks = learning_repo.list_class_feedback(db, class_id)
    return [_serialize_feedback(f) for f in feedbacks]


@router.get("/feedback/{feedback_id}", response_model=ClassFeedbackResponse)
def get_feedback_detail(
    feedback_id: int,
    current_user: User = Depends(require_role(UserRole.TEACHER)),
    db: Session = Depends(get_db),
):
    feedback = learning_repo.get_class_feedback(db, feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")
    if not class_repo.user_owns_class(db, current_user, feedback.class_id):
        raise HTTPException(status_code=403, detail="无权查看该反馈")
    return _serialize_feedback(feedback)


@router.post(
    "/me/report",
    response_model=LearningGenerationJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_my_report(
    class_id: int = Query(...),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    if not class_repo.user_can_access_class(db, current_user, class_id):
        raise HTTPException(status_code=403, detail="您未加入该班级")
    reports = learning_repo.list_student_reports(
        db, current_user.id, class_id, limit=1
    )
    if reports:
        total_message_count = conversation_repo.count_student_messages_in_class(
            db, current_user.id, class_id
        )
        if total_message_count <= reports[0].message_count:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="暂无新的学习记录，请先继续学习交流",
            )
    job = enqueue_student_report(
        db,
        class_id=class_id,
        student_id=current_user.id,
        requested_by=current_user.id,
    )
    return serialize_learning_job(db, job, include_result=False)


@router.get("/jobs/{job_id}", response_model=LearningGenerationJobResponse)
def get_learning_generation_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = learning_repo.get_learning_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="学情任务不存在")
    if job.requested_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看该学情任务")
    return serialize_learning_job(db, job)

@router.get("/assistant-status")
def get_learning_assistant_status(
    class_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the compact, role-aware state used by the chat-page mascot."""
    readiness_threshold = 5

    if current_user.role == UserRole.STUDENT:
        if not class_repo.user_can_access_class(db, current_user, class_id):
            raise HTTPException(status_code=403, detail="您尚未加入该班级")

        effective_count = conversation_repo.count_effective_student_questions_in_class(
            db, current_user.id, class_id
        )
        total_message_count = conversation_repo.count_student_messages_in_class(
            db, current_user.id, class_id
        )
        reports = learning_repo.list_student_reports(db, current_user.id, class_id, limit=1)
        latest_report = _serialize_report(reports[0], current_user.name) if reports else None
        active_job = learning_repo.get_active_learning_job(
            db,
            kind=STUDENT_REPORT_JOB,
            class_id=class_id,
            student_id=current_user.id,
        )
        return {
            "role": "student",
            "class_id": class_id,
            "effective_question_count": effective_count,
            "can_generate": effective_count >= readiness_threshold,
            "has_updates": bool(latest_report and total_message_count > latest_report["message_count"]),
            "latest_report": latest_report,
            "generation_job": (
                serialize_learning_job(db, active_job, include_result=False)
                if active_job else None
            ),
        }

    if current_user.role == UserRole.TEACHER:
        _ensure_teacher_class_access(db, current_user, class_id)
        students = class_repo.list_class_students(db, class_id)
        student_states = []
        for student in students:
            effective_count = conversation_repo.count_effective_student_questions_in_class(
                db, student["id"], class_id
            )
            reports = learning_repo.list_student_reports(db, student["id"], class_id, limit=1)
            active_job = learning_repo.get_active_learning_job(
                db,
                kind=STUDENT_REPORT_JOB,
                class_id=class_id,
                student_id=student["id"],
            )
            student_states.append({
                "id": student["id"],
                "name": student["name"],
                "effective_question_count": effective_count,
                "ready": effective_count >= readiness_threshold,
                "latest_report": _serialize_report(reports[0], student["name"]) if reports else None,
                "generation_job": (
                    serialize_learning_job(db, active_job, include_result=False)
                    if active_job else None
                ),
            })

        feedbacks = learning_repo.list_class_feedback(db, class_id, limit=1)
        active_feedback_job = learning_repo.get_active_learning_job(
            db,
            kind=CLASS_FEEDBACK_JOB,
            class_id=class_id,
        )
        active_students = sum(1 for student in student_states if student["effective_question_count"] > 0)
        return {
            "role": "teacher",
            "class_id": class_id,
            "student_count": len(student_states),
            "active_students": active_students,
            "ready_students": sum(1 for student in student_states if student["ready"]),
            "total_effective_questions": sum(
                student["effective_question_count"] for student in student_states
            ),
            "students": sorted(
                student_states,
                key=lambda student: (student["ready"], student["effective_question_count"]),
                reverse=True,
            ),
            "latest_feedback": _serialize_feedback(feedbacks[0]) if feedbacks else None,
            "generation_job": (
                serialize_learning_job(db, active_feedback_job, include_result=False)
                if active_feedback_job else None
            ),
        }

    raise HTTPException(status_code=400, detail="请先选择身份")
