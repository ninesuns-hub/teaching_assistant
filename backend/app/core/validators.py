import re

TONGJI_EMAIL_PATTERN = re.compile(r"^[^@\s]+@tongji\.edu\.cn$")


def is_valid_tongji_email(email: str) -> bool:
    return bool(TONGJI_EMAIL_PATTERN.match(email.strip().lower()))
