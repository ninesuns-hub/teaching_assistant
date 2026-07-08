"""将调试账号密码重置为 1"""
import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from database.mysql_db import SessionLocal, User
from app.core.auth import get_password_hash

DEBUG_EMAILS = [
    "1111111@tongji.edu.cn",
    "2353169@tongji.edu.cn",
]
PASSWORD = "1"


def main():
    db = SessionLocal()
    hashed = get_password_hash(PASSWORD)
    for email in DEBUG_EMAILS:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.hashed_password = hashed
            print(f"已重置: {email} ({user.role.value if user.role else 'no role'})")
        else:
            print(f"未找到: {email}")
    db.commit()
    db.close()
    print("密码已全部设为: 1")


if __name__ == "__main__":
    main()
