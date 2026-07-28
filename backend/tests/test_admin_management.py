import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.deps import is_effective_admin, require_admin
from app.interfaces.api import admin_routes, auth_routes
from app.interfaces.api.schemas import UserLogin
from app.core.auth import get_password_hash
from database.mysql_db import AdminAuditLog, Base, ClassMember, ClassRoom, User, UserRole


class AdminManagementTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.admin = User(email="1000001@tongji.edu.cn", name="Admin", hashed_password="x", role=UserRole.TEACHER, is_admin=True, status="active")
        self.student = User(email="1000002@tongji.edu.cn", name="Student", hashed_password="x", role=UserRole.STUDENT, status="active")
        self.teacher = User(email="1000003@tongji.edu.cn", name="Teacher", hashed_password="x", role=UserRole.TEACHER, status="active")
        self.db.add_all([self.admin, self.student, self.teacher])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_bootstrap_admin_is_effective_without_database_flag(self):
        self.student.is_admin = False
        with patch.dict(os.environ, {"ADMIN_EMAILS": self.student.email}):
            self.assertTrue(is_effective_admin(self.student))

    def test_regular_user_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            require_admin(self.student)
        self.assertEqual(raised.exception.status_code, 403)

    def test_student_role_change_is_blocked_until_membership_removed(self):
        classroom = ClassRoom(name="Class A", invite_code="ABC123", teacher_id=self.teacher.id)
        self.db.add(classroom)
        self.db.flush()
        self.db.add(ClassMember(class_id=classroom.id, student_id=self.student.id))
        self.db.commit()
        with self.assertRaises(HTTPException) as raised:
            admin_routes.update_role(self.student.id, admin_routes.RoleUpdate(role="teacher"), self.admin, self.db)
        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("Class A", raised.exception.detail)

    def test_teacher_role_change_requires_class_transfer(self):
        classroom = ClassRoom(name="Class B", invite_code="DEF456", teacher_id=self.teacher.id)
        self.db.add(classroom)
        self.db.commit()
        with self.assertRaises(HTTPException):
            admin_routes.update_role(self.teacher.id, admin_routes.RoleUpdate(role="student"), self.admin, self.db)
        admin_routes.transfer_class(classroom.id, admin_routes.ClassTransferRequest(teacher_id=self.admin.id), self.admin, self.db)
        result = admin_routes.update_role(self.teacher.id, admin_routes.RoleUpdate(role="student"), self.admin, self.db)
        self.assertEqual(result["role"], "student")

    def test_profile_update_writes_audit_log(self):
        result = admin_routes.update_profile(self.student.id, admin_routes.ProfileUpdate(name="New Name", reason="correction"), self.admin, self.db)
        self.assertEqual(result["name"], "New Name")
        audit = self.db.query(AdminAuditLog).one()
        self.assertEqual(audit.action, "user.profile.update")
        self.assertEqual(audit.reason, "correction")

    def test_disabled_user_cannot_login(self):
        self.student.hashed_password = get_password_hash("password123")
        self.student.status = "disabled"
        self.db.commit()
        with self.assertRaises(HTTPException) as raised:
            auth_routes.login(UserLogin(email=self.student.email, password="password123"), self.db)
        self.assertEqual(raised.exception.status_code, 403)

    def test_admin_cannot_disable_self(self):
        with self.assertRaises(HTTPException) as raised:
            admin_routes.update_status(self.admin.id, admin_routes.StatusUpdate(status="disabled"), self.admin, self.db)
        self.assertEqual(raised.exception.status_code, 400)

    def test_user_list_filters_and_paginates(self):
        result = admin_routes.list_users(search="Student", role="student", account_status="active", page=1, page_size=1, _=self.admin, db=self.db)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["email"], self.student.email)


if __name__ == "__main__":
    unittest.main()
