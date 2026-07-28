import os
import tempfile

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from agent_core.config.settings import settings
from app.core.redis_client import redis_client
from database.mysql_db import engine
from database.vector_repo import get_qdrant_client


router = APIRouter()


@router.get("/health/live")
def live() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
def ready():
    components = {
        "mysql": False,
        "redis": False,
        "storage": False,
        "qdrant": False,
    }

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        components["mysql"] = True
    except Exception:
        pass

    try:
        components["redis"] = bool(redis_client.client.ping())
    except Exception:
        pass

    try:
        os.makedirs(settings.STORAGE_DIR, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=settings.STORAGE_DIR):
            pass
        components["storage"] = True
    except Exception:
        pass

    try:
        client = get_qdrant_client()
        collections = {
            collection.name
            for collection in client.get_collections().collections
        }
        if settings.QDRANT_COLLECTION_NAME in collections:
            collection = client.get_collection(settings.QDRANT_COLLECTION_NAME)
            configured_size = getattr(
                collection.config.params.vectors,
                "size",
                None,
            )
            components["qdrant"] = configured_size == settings.EMBED_DIMENSION
    except Exception:
        pass

    is_ready = all(components.values())
    payload = {
        "status": "ready" if is_ready else "not_ready",
        "components": components,
    }
    if is_ready:
        return payload
    return JSONResponse(status_code=503, content=payload)
