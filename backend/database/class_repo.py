import os
import logging
import re
from typing import List, Optional
from sqlalchemy.orm import Session
from database.mysql_db import (
    ClassRoom,
    ClassMember,
    ClassMaterial,
    User,
    UserRole,
    generate_invite_code,
)
from agent_core.config.settings import settings

logger = logging.getLogger(__name__)


def _unique_invite_code(db: Session) -> str:
    while True:
        code = generate_invite_code()
        if not db.query(ClassRoom).filter(ClassRoom.invite_code == code).first():
            return code


def create_class(db: Session, teacher: User, name: str) -> ClassRoom:
    classroom = ClassRoom(
        name=name.strip(),
        invite_code=_unique_invite_code(db),
        teacher_id=teacher.id,
    )
    db.add(classroom)
    db.commit()
    db.refresh(classroom)
    os.makedirs(os.path.join(settings.CLASS_MATERIALS_DIR, str(classroom.id)), exist_ok=True)
    return classroom


def get_user_classes(db: Session, user: User) -> List[dict]:
    results = []
    if user.role == UserRole.TEACHER:
        for c in db.query(ClassRoom).filter(ClassRoom.teacher_id == user.id).all():
            results.append({
                "id": c.id,
                "name": c.name,
                "invite_code": c.invite_code,
                "teacher_id": c.teacher_id,
                "role_in_class": "owner",
            })
    elif user.role == UserRole.STUDENT:
        memberships = db.query(ClassMember).filter(ClassMember.student_id == user.id).all()
        for m in memberships:
            c = m.classroom
            results.append({
                "id": c.id,
                "name": c.name,
                "invite_code": c.invite_code,
                "teacher_id": c.teacher_id,
                "role_in_class": "member",
            })
    return results


def join_class(db: Session, student: User, invite_code: str) -> ClassRoom:
    classroom = db.query(ClassRoom).filter(ClassRoom.invite_code == invite_code.strip().upper()).first()
    if not classroom:
        raise ValueError("邀请码无效")

    exists = db.query(ClassMember).filter(
        ClassMember.class_id == classroom.id,
        ClassMember.student_id == student.id,
    ).first()
    if exists:
        raise ValueError("您已在该班级中")

    db.add(ClassMember(class_id=classroom.id, student_id=student.id))
    db.commit()
    return classroom


def user_can_access_class(db: Session, user: User, class_id: int) -> bool:
    classroom = db.query(ClassRoom).filter(ClassRoom.id == class_id).first()
    if not classroom:
        return False
    if user.role == UserRole.TEACHER and classroom.teacher_id == user.id:
        return True
    if user.role == UserRole.STUDENT:
        return db.query(ClassMember).filter(
            ClassMember.class_id == class_id,
            ClassMember.student_id == user.id,
        ).first() is not None
    return False


def user_owns_class(db: Session, user: User, class_id: int) -> bool:
    classroom = db.query(ClassRoom).filter(ClassRoom.id == class_id).first()
    return classroom is not None and user.role == UserRole.TEACHER and classroom.teacher_id == user.id


def list_materials(db: Session, class_id: int) -> List[ClassMaterial]:
    materials = db.query(ClassMaterial).filter(ClassMaterial.class_id == class_id).all()

    def natural_name_key(material: ClassMaterial):
        return [
            (0, int(part)) if part.isdigit() else (1, part.casefold())
            for part in re.split(r"(\d+)", material.filename or "")
        ]

    return sorted(materials, key=natural_name_key)


def get_material(db: Session, class_id: int, material_id: int) -> Optional[ClassMaterial]:
    return db.query(ClassMaterial).filter(
        ClassMaterial.id == material_id,
        ClassMaterial.class_id == class_id,
    ).first()


def get_material_by_name_and_type(
    db: Session, class_id: int, filename: str
) -> Optional[ClassMaterial]:
    target_stem, target_ext = os.path.splitext(filename.strip())
    target_stem = target_stem.casefold()
    target_ext = target_ext.casefold()
    materials = db.query(ClassMaterial).filter(
        ClassMaterial.class_id == class_id,
    ).all()
    for material in materials:
        stem, ext = os.path.splitext(material.filename or "")
        if stem.casefold() == target_stem and ext.casefold() == target_ext:
            return material
    return None


def delete_material(db: Session, material: ClassMaterial) -> None:
    db.delete(material)
    db.commit()


def list_class_students(db: Session, class_id: int) -> List[dict]:
    members = db.query(ClassMember).filter(ClassMember.class_id == class_id).all()
    results = []
    for m in members:
        student = m.student
        results.append({
            "id": student.id,
            "name": student.name,
            "email": student.email,
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
        })
    return results


def add_student_to_class(db: Session, class_id: int, student_id: int) -> ClassMember:
    existing = db.query(ClassMember).filter(
        ClassMember.class_id == class_id,
        ClassMember.student_id == student_id,
    ).first()
    if existing:
        return existing
    member = ClassMember(class_id=class_id, student_id=student_id)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def remove_student_from_class(db: Session, class_id: int, student_id: int) -> bool:
    member = db.query(ClassMember).filter(
        ClassMember.class_id == class_id,
        ClassMember.student_id == student_id,
    ).first()
    if not member:
        return False
    db.delete(member)
    db.commit()
    return True


def add_material(
    db: Session,
    class_id: int,
    filename: str,
    file_path: str,
    file_type: str,
    file_size: int,
    uploader_id: int,
    content_hash: str | None = None,
) -> ClassMaterial:
    material = ClassMaterial(
        class_id=class_id,
        filename=filename,
        file_path=file_path,
        file_type=file_type,
        file_size=file_size,
        content_hash=content_hash,
        uploaded_by=uploader_id,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material
