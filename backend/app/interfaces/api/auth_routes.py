from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from database.mysql_db import get_db, User, UserRole
from .schemas import (
    SendCodeRequest,
    UserRegister,
    UserLogin,
    SelectRoleRequest,
    Token,
    UserProfile,
)
from app.core.auth import get_password_hash, verify_password, create_access_token
from app.core.redis_client import redis_client
from app.core.email_service import send_verification_email, generate_code
from app.core.validators import is_valid_tongji_email
from app.core.deps import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_token(user: User) -> Token:
    access_token = create_access_token(data={"sub": user.email, "role": user.role.value if user.role else None})
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role.value if user.role else None,
        name=user.name,
        email=user.email,
        needs_role_selection=user.role is None,
    )


@router.post("/send-code")
async def send_code(payload: SendCodeRequest):
    email = payload.email.strip().lower()
    if not is_valid_tongji_email(email):
        raise HTTPException(status_code=400, detail="请使用同济大学学校邮箱，格式：7位学号@tongji.edu.cn")

    if not redis_client.can_send_code(email):
        raise HTTPException(status_code=429, detail="验证码发送过于频繁，请 60 秒后再试")

    code = generate_code()
    redis_client.set_code(email, code)
    redis_client.mark_code_sent(email)
    await send_verification_email(email, code)
    return {"message": "验证码已发送。若未收到邮件，请查看后端日志中的验证码。"}


@router.post("/register", response_model=Token)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    email = user_data.email.strip().lower()
    if not is_valid_tongji_email(email):
        raise HTTPException(status_code=400, detail="请使用同济大学学校邮箱，格式：7位学号@tongji.edu.cn")

    stored_code = redis_client.get_code(email)
    if not stored_code or stored_code != user_data.code.strip():
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="该邮箱已被注册")

    new_user = User(
        email=email,
        name=user_data.name,
        hashed_password=get_password_hash(user_data.password),
        role=None,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    redis_client.delete_code(email)

    return _build_token(new_user)


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    email = user_data.email.strip().lower()
    db_user = db.query(User).filter(User.email == email).first()
    if not db_user or not verify_password(user_data.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    return _build_token(db_user)


@router.post("/select-role", response_model=Token)
async def select_role(
    payload: SelectRoleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role is not None:
        raise HTTPException(status_code=400, detail="身份已选择，不可重复修改")

    try:
        role = UserRole(payload.role.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的身份类型，请选择 student 或 teacher")

    current_user.role = role
    db.commit()
    return _build_token(current_user)


@router.get("/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role.value if current_user.role else None,
        needs_role_selection=current_user.role is None,
    )
