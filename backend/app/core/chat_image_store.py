import base64
import os
import re
import uuid
from typing import Tuple

from agent_core.config.settings import settings

ALLOWED_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
MAX_BYTES = 5 * 1024 * 1024


def get_chat_images_dir() -> str:
    os.makedirs(settings.CHAT_IMAGES_DIR, exist_ok=True)
    return settings.CHAT_IMAGES_DIR


def save_chat_image(user_id: int, image_base64: str, mime_type: str) -> str:
    mime = (mime_type or "image/jpeg").lower()
    if mime not in ALLOWED_MIME:
        raise ValueError("仅支持 JPG、PNG、WEBP、GIF 图片")

    raw = image_base64.strip()
    if raw.startswith("data:"):
        raw = raw.split(",", 1)[-1]
    try:
        content = base64.b64decode(raw, validate=True)
    except Exception as exc:
        raise ValueError("图片数据无效") from exc

    if len(content) > MAX_BYTES:
        raise ValueError("图片大小不能超过 5MB")

    ext = ALLOWED_MIME[mime]
    user_dir = os.path.join(get_chat_images_dir(), str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(user_dir, filename)
    with open(file_path, "wb") as f:
        f.write(content)

    return f"{user_id}/{filename}"


def resolve_image_path(relative_path: str) -> str:
    if not relative_path or ".." in relative_path:
        raise ValueError("无效图片路径")
    if not re.match(r"^\d+/[a-f0-9]+\.(jpg|png|webp|gif)$", relative_path):
        raise ValueError("无效图片路径")
    full = os.path.join(get_chat_images_dir(), relative_path)
    if not os.path.isfile(full):
        raise FileNotFoundError("图片不存在")
    return full


def image_url_for_path(relative_path: str | None) -> str | None:
    if not relative_path:
        return None
    return f"/api/chat/images/{relative_path}"
