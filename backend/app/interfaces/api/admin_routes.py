import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.deps import is_bootstrap_admin, is_effective_admin, require_admin
from database.mysql_db import (
    AdminAuditLog,
    ClassMember,
    ClassRoom,
    Conversation,
    HomeworkSubmission,
    StudentLearningReport,
    User,
    UserRole,
    get_db,
)

router = APIRouter()


class ReasonedRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class ProfileUpdate(ReasonedRequest):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()


class RoleUpdate(ReasonedRequest):
    role: str


class StatusUpdate(ReasonedRequest):
    status: str


class AdminAccessUpdate(ReasonedRequest):
    is_admin: bool


class MembershipUpdate(ReasonedRequest):
    class_id: int


class ClassTransferRequest(ReasonedRequest):
    teacher_id: int


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _audit(db: Session, actor: User, target_id: int | None, action: str, before, after, reason=None):
    db.add(AdminAuditLog(
        actor_user_id=actor.id,
        target_user_id=target_id,
        action=action,
        before_json=_json(before) if before is not None else None,
        after_json=_json(after) if after is not None else None,
        reason=(reason or "").strip() or None,
    ))


def _get_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def _class_data(db: Session, user: User) -> list[dict]:
    owned = db.query(ClassRoom).filter(ClassRoom.teacher_id == user.id).all()
    memberships = (
        db.query(ClassMember, ClassRoom)
        .join(ClassRoom, ClassRoom.id == ClassMember.class_id)
        .filter(ClassMember.student_id == user.id)
        .all()
    )
    return [
        {"id": item.id, "name": item.name, "relation": "owner", "teacher_id": item.teacher_id}
        for item in owned
    ] + [
        {"id": room.id, "name": room.name, "relation": "member", "teacher_id": room.teacher_id}
        for _, room in memberships
    ]


def _learning_overview(db: Session, user: User) -> dict:
    conversations = db.query(func.count(Conversation.id), func.max(Conversation.updated_at)).filter(Conversation.user_id == user.id).one()
    submissions = db.query(func.count(HomeworkSubmission.id), func.max(HomeworkSubmission.submitted_at)).filter(HomeworkSubmission.student_id == user.id).one()
    report_count = db.query(func.count(StudentLearningReport.id)).filter(StudentLearningReport.student_id == user.id).scalar() or 0
    dates = [value for value in (conversations[1], submissions[1], user.last_login_at) if value]
    return {
        "class_count": len(_class_data(db, user)),
        "conversation_count": int(conversations[0] or 0),
        "submission_count": int(submissions[0] or 0),
        "report_count": int(report_count),
        "last_activity_at": max(dates).isoformat() if dates else None,
    }


def _serialize_user(db: Session, user: User, include_classes: bool = False) -> dict:
    data = {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role.value if user.role else None,
        "status": user.status,
        "is_admin": bool(user.is_admin),
        "is_bootstrap_admin": is_bootstrap_admin(user),
        "effective_admin": is_effective_admin(user),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "learning_overview": _learning_overview(db, user),
    }
    if include_classes:
        data["classes"] = _class_data(db, user)
    return data


@router.get("/classes")
def list_classes(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(ClassRoom).order_by(ClassRoom.name.asc(), ClassRoom.id.asc()).all()
    teachers = {user.id: user.name for user in db.query(User).filter(User.id.in_({row.teacher_id for row in rows})).all()} if rows else {}
    return [{"id": row.id, "name": row.name, "teacher_id": row.teacher_id, "teacher_name": teachers.get(row.teacher_id)} for row in rows]

@router.get("/users")
def list_users(
    search: str | None = None,
    role: str | None = None,
    account_status: str | None = Query(None, alias="status"),
    class_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(or_(User.name.ilike(term), User.email.ilike(term)))
    if role:
        try:
            query = query.filter(User.role == UserRole(role))
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的身份筛选")
    if account_status:
        if account_status not in {"active", "disabled"}:
            raise HTTPException(status_code=400, detail="无效的账号状态")
        query = query.filter(User.status == account_status)
    if class_id is not None:
        member_ids = db.query(ClassMember.student_id).filter(ClassMember.class_id == class_id)
        query = query.filter(or_(User.id.in_(member_ids), User.id == db.query(ClassRoom.teacher_id).filter(ClassRoom.id == class_id).scalar_subquery()))
    total = query.count()
    users = query.order_by(User.created_at.desc(), User.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_serialize_user(db, user) for user in users], "page": page, "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size}


@router.get("/users/{user_id}")
def get_user_detail(user_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return _serialize_user(db, _get_user(db, user_id), include_classes=True)


@router.patch("/users/{user_id}/profile")
def update_profile(user_id: int, payload: ProfileUpdate, actor: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = _get_user(db, user_id)
    before = {"name": user.name}
    user.name = payload.name
    _audit(db, actor, user.id, "user.profile.update", before, {"name": user.name}, payload.reason)
    db.commit()
    db.refresh(user)
    return _serialize_user(db, user, include_classes=True)


@router.patch("/users/{user_id}/role")
def update_role(user_id: int, payload: RoleUpdate, actor: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = _get_user(db, user_id)
    try:
        next_role = UserRole(payload.role)
    except ValueError:
        raise HTTPException(status_code=400, detail="身份必须是 student 或 teacher")
    if user.role == UserRole.STUDENT and next_role == UserRole.TEACHER:
        classes = _class_data(db, user)
        if classes:
            raise HTTPException(status_code=409, detail="请先移除该学生的班级成员关系：" + "、".join(item["name"] for item in classes if item["relation"] == "member"))
    if user.role == UserRole.TEACHER and next_role == UserRole.STUDENT:
        owned = [item for item in _class_data(db, user) if item["relation"] == "owner"]
        if owned:
            raise HTTPException(status_code=409, detail="请先转交该教师负责的班级：" + "、".join(item["name"] for item in owned))
    before = {"role": user.role.value if user.role else None}
    user.role = next_role
    _audit(db, actor, user.id, "user.role.update", before, {"role": next_role.value}, payload.reason)
    db.commit()
    return _serialize_user(db, user, include_classes=True)


@router.patch("/users/{user_id}/status")
def update_status(user_id: int, payload: StatusUpdate, actor: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = _get_user(db, user_id)
    if payload.status not in {"active", "disabled"}:
        raise HTTPException(status_code=400, detail="状态必须是 active 或 disabled")
    if user.id == actor.id and payload.status == "disabled":
        raise HTTPException(status_code=400, detail="不能停用自己的账号")
    if payload.status == "disabled" and user.role == UserRole.TEACHER:
        owned = db.query(ClassRoom).filter(ClassRoom.teacher_id == user.id).all()
        if owned:
            raise HTTPException(status_code=409, detail="请先转交该教师负责的班级：" + "、".join(item.name for item in owned))
    before = {"status": user.status}
    user.status = payload.status
    _audit(db, actor, user.id, "user.status.update", before, {"status": user.status}, payload.reason)
    db.commit()
    return _serialize_user(db, user, include_classes=True)


@router.patch("/users/{user_id}/admin-access")
def update_admin_access(user_id: int, payload: AdminAccessUpdate, actor: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = _get_user(db, user_id)
    if not payload.is_admin and is_bootstrap_admin(user):
        raise HTTPException(status_code=400, detail="环境变量管理员不能在页面中撤权")
    if user.id == actor.id and not payload.is_admin:
        raise HTTPException(status_code=400, detail="不能撤销自己的管理员权限")
    before = {"is_admin": bool(user.is_admin)}
    user.is_admin = payload.is_admin
    _audit(db, actor, user.id, "user.admin_access.update", before, {"is_admin": bool(user.is_admin)}, payload.reason)
    db.commit()
    return _serialize_user(db, user, include_classes=True)


@router.post("/users/{user_id}/class-memberships", status_code=status.HTTP_201_CREATED)
def add_membership(user_id: int, payload: MembershipUpdate, actor: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = _get_user(db, user_id)
    if user.role != UserRole.STUDENT:
        raise HTTPException(status_code=400, detail="只有学生可以加入班级")
    classroom = db.query(ClassRoom).filter(ClassRoom.id == payload.class_id).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="班级不存在")
    existing = db.query(ClassMember).filter(ClassMember.class_id == classroom.id, ClassMember.student_id == user.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="学生已在该班级中")
    db.add(ClassMember(class_id=classroom.id, student_id=user.id))
    _audit(db, actor, user.id, "user.class_membership.add", None, {"class_id": classroom.id, "class_name": classroom.name}, payload.reason)
    db.commit()
    return _serialize_user(db, user, include_classes=True)


@router.delete("/users/{user_id}/class-memberships/{class_id}")
def remove_membership(user_id: int, class_id: int, reason: str | None = Query(None, max_length=500), actor: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = _get_user(db, user_id)
    member = db.query(ClassMember).filter(ClassMember.class_id == class_id, ClassMember.student_id == user.id).first()
    if not member:
        raise HTTPException(status_code=404, detail="班级成员关系不存在")
    classroom = db.query(ClassRoom).filter(ClassRoom.id == class_id).first()
    before = {"class_id": class_id, "class_name": classroom.name if classroom else None}
    db.delete(member)
    _audit(db, actor, user.id, "user.class_membership.remove", before, None, reason)
    db.commit()
    return _serialize_user(db, user, include_classes=True)


@router.post("/classes/{class_id}/transfer")
def transfer_class(class_id: int, payload: ClassTransferRequest, actor: User = Depends(require_admin), db: Session = Depends(get_db)):
    classroom = db.query(ClassRoom).filter(ClassRoom.id == class_id).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="班级不存在")
    teacher = _get_user(db, payload.teacher_id)
    if teacher.role != UserRole.TEACHER or teacher.status != "active":
        raise HTTPException(status_code=400, detail="接收人必须是有效教师")
    before = {"teacher_id": classroom.teacher_id}
    classroom.teacher_id = teacher.id
    _audit(db, actor, teacher.id, "class.owner.transfer", before, {"class_id": classroom.id, "teacher_id": teacher.id}, payload.reason)
    db.commit()
    return {"id": classroom.id, "name": classroom.name, "teacher_id": classroom.teacher_id}


@router.get("/audit-logs")
def list_audit_logs(target_user_id: int | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), _: User = Depends(require_admin), db: Session = Depends(get_db)):
    query = db.query(AdminAuditLog)
    if target_user_id is not None:
        query = query.filter(AdminAuditLog.target_user_id == target_user_id)
    total = query.count()
    rows = query.order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    actor_ids = {row.actor_user_id for row in rows}
    actors = {user.id: user.name for user in db.query(User).filter(User.id.in_(actor_ids)).all()} if actor_ids else {}
    return {"items": [{"id": row.id, "actor_user_id": row.actor_user_id, "actor_name": actors.get(row.actor_user_id), "target_user_id": row.target_user_id, "action": row.action, "before": json.loads(row.before_json) if row.before_json else None, "after": json.loads(row.after_json) if row.after_json else None, "reason": row.reason, "created_at": row.created_at.isoformat()} for row in rows], "page": page, "page_size": page_size, "total": total}
