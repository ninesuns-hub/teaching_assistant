import random
import string
import aiosmtplib
from email.message import EmailMessage
from agent_core.config.settings import settings
import logging

logger = logging.getLogger(__name__)

PLACEHOLDER_MARKERS = ("your_email", "your_password", "example.com")


def _smtp_configured() -> bool:
    user = (settings.SMTP_USER or "").strip()
    password = (settings.SMTP_PASSWORD or "").strip()
    if not user or not password:
        return False
    lowered = f"{user}{password}".lower()
    return not any(marker in lowered for marker in PLACEHOLDER_MARKERS)


async def send_verification_email(email: str, code: str) -> bool:
    """
    发送验证码邮件。
    未配置 SMTP 或发送失败时，开发模式下降级为日志输出（验证码已写入 Redis）。
    """
    if not _smtp_configured():
        logger.warning(f"[开发模式] 验证码: {code} -> {email}")
        return True

    message = EmailMessage()
    message["From"] = settings.SMTP_USER
    message["To"] = email
    message["Subject"] = "离散数学助教系统 - 注册验证码"
    message.set_content(f"您的注册验证码为: {code}，有效期为5分钟。请勿泄露给他人。")

    try:
        if settings.SMTP_PORT == 465:
            async with aiosmtplib.SMTP(
                hostname=settings.SMTP_HOST,
                port=465,
                use_tls=True,
                timeout=15,
            ) as smtp:
                await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                await smtp.send_message(message)
        else:
            async with aiosmtplib.SMTP(
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                start_tls=True,
                timeout=15,
            ) as smtp:
                await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                await smtp.send_message(message)
        logger.info(f"验证码邮件已发送至 {email}")
        return True
    except Exception as e:
        logger.error(f"发送邮件失败: {e}")
        logger.warning(f"[降级模式] 验证码: {code} -> {email}（请查看后端日志）")
        return True


def generate_code(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))
