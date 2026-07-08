from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from database.mysql_db import get_db, User, UserRole
from database import class_repo, conversation_repo, learning_repo
from app.core.deps import get_current_user, require_role
from app.services.learning_service import (
    generate_student_report_record as generate_student_report,
    generate_class_feedback_record as generate_class_feedback,
    _serialize_report,
    _serialize_feedback,
)
from .schemas import StudentBriefResponse, LearningReportResponse, ClassFeedbackResponse

router = APIRouter()


def _ensure_teacher_class_access(db: Session, user: User, class_id: int):
    if not class_repo.user_owns_class(db, user, class_id):
        raise HTTPException(status_code=403, detail="无权访问该班级")


@router.get("/classes/{class_id}/students", response_model=list[StudentBriefResponse])
async def list_class_students(
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
        )
        for s in students
    ]


@router.post("/classes/{class_id}/students/{student_id}/report", response_model=LearningReportResponse)
async def create_student_report(
    class_id: int,
    student_id: int,
    current_user: User = Depends(require_role(UserRole.TEACHER)),
    db: Session = Depends(get_db),
):
    _ensure_teacher_class_access(db, current_user, class_id)
    member_ids = {s["id"] for s in class_repo.list_class_students(db, class_id)}
    if student_id not in member_ids:
        raise HTTPException(status_code=400, detail="该学生不在本班级中")
    try:
        return generate_student_report(db, student_id, class_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/classes/{class_id}/students/{student_id}/reports", response_model=list[LearningReportResponse])
async def list_student_reports(
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
async def get_report_detail(
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


@router.post("/classes/{class_id}/feedback", response_model=ClassFeedbackResponse)
async def create_class_feedback(
    class_id: int,
    current_user: User = Depends(require_role(UserRole.TEACHER)),
    db: Session = Depends(get_db),
):
    _ensure_teacher_class_access(db, current_user, class_id)
    try:
        return generate_class_feedback(db, class_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/classes/{class_id}/feedback", response_model=list[ClassFeedbackResponse])
async def list_class_feedback(
    class_id: int,
    current_user: User = Depends(require_role(UserRole.TEACHER)),
    db: Session = Depends(get_db),
):
    _ensure_teacher_class_access(db, current_user, class_id)
    feedbacks = learning_repo.list_class_feedback(db, class_id)
    return [_serialize_feedback(f) for f in feedbacks]


@router.get("/feedback/{feedback_id}", response_model=ClassFeedbackResponse)
async def get_feedback_detail(
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


@router.post("/me/report", response_model=LearningReportResponse)
async def create_my_report(
    class_id: int = Query(...),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    if not class_repo.user_can_access_class(db, current_user, class_id):
        raise HTTPException(status_code=403, detail="您未加入该班级")
    try:
        return generate_student_report(db, current_user.id, class_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
