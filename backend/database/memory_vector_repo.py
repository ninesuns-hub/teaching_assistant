import logging
import uuid
from typing import Optional

from qdrant_client.http import models

from agent_core.config.settings import settings
from database.vector_repo import get_qdrant_client, _embed, _embed_query

logger = logging.getLogger(__name__)
_ready = False


def init_collection() -> None:
    global _ready
    if _ready:
        return
    client = get_qdrant_client()
    collections = client.get_collections().collections
    if not any(item.name == settings.QDRANT_MEMORY_COLLECTION_NAME for item in collections):
        client.create_collection(
            collection_name=settings.QDRANT_MEMORY_COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=1536,
                distance=models.Distance.COSINE,
            ),
        )
    if not settings.QDRANT_PATH:
        collection = client.get_collection(settings.QDRANT_MEMORY_COLLECTION_NAME)
        schema = collection.payload_schema or {}
        for field in ("user_id", "class_id", "memory_type", "status"):
            if field not in schema:
                client.create_payload_index(
                    collection_name=settings.QDRANT_MEMORY_COLLECTION_NAME,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                    wait=True,
                )
    _ready = True


def upsert_memory(memory) -> None:
    init_collection()
    vector = _embed([memory.content])[0]
    get_qdrant_client().upsert(
        collection_name=settings.QDRANT_MEMORY_COLLECTION_NAME,
        points=[models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"memory:{memory.public_id}")),
            vector=vector,
            payload={
                "public_id": memory.public_id,
                "user_id": str(memory.user_id),
                "class_id": str(memory.class_id) if memory.class_id is not None else "global",
                "memory_type": memory.memory_type,
                "status": memory.status,
                "content": memory.content,
            },
        )],
    )


def delete_memory(public_id: str) -> None:
    client = get_qdrant_client()
    collections = client.get_collections().collections
    if not any(item.name == settings.QDRANT_MEMORY_COLLECTION_NAME for item in collections):
        return
    client.delete(
        collection_name=settings.QDRANT_MEMORY_COLLECTION_NAME,
        points_selector=models.PointIdsList(points=[
            str(uuid.uuid5(uuid.NAMESPACE_URL, f"memory:{public_id}"))
        ]),
    )


def query_memories(
    question: str,
    *,
    user_id: int,
    class_id: Optional[int],
    limit: int = 5,
    request_id: Optional[str] = None,
) -> list[dict]:
    init_collection()
    vector = _embed_query(question, request_id=request_id)
    allowed_classes = ["global"]
    if class_id is not None:
        allowed_classes.append(str(class_id))
    result = get_qdrant_client().query_points(
        collection_name=settings.QDRANT_MEMORY_COLLECTION_NAME,
        query=vector,
        query_filter=models.Filter(must=[
            models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id))),
            models.FieldCondition(key="class_id", match=models.MatchAny(any=allowed_classes)),
            models.FieldCondition(key="status", match=models.MatchValue(value="active")),
        ]),
        limit=limit,
        with_payload=True,
    )
    return [
        {**(point.payload or {}), "similarity": float(point.score)}
        for point in result.points
    ]
