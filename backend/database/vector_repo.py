import os
import uuid
import logging
import json
import threading
import time
from collections import OrderedDict
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models
from openai import OpenAI
from agent_core.config.settings import settings

logger = logging.getLogger(__name__)

# ── OpenAI 客户端 (专用 Embedding) ──
_embed_client = None
_query_embedding_cache = OrderedDict()
_query_embedding_cache_lock = threading.Lock()
_QUERY_CACHE_MAX_SIZE = 512
_QUERY_CACHE_TTL_SECONDS = 3600

def get_embed_client():
    global _embed_client
    if _embed_client is None:
        _embed_client = OpenAI(
            api_key=settings.EMBED_API_KEY,
            base_url=settings.EMBED_BASE_URL
        )
    return _embed_client

# ── Qdrant 客户端 ──
_qdrant_client = None
_payload_index_checked = False
_collection_ready = False

def get_qdrant_client():
    global _qdrant_client
    if _qdrant_client is None:
        # 如果提供了 QDRANT_PATH，则使用本地存储模式
        if settings.QDRANT_PATH:
            _qdrant_client = QdrantClient(path=settings.QDRANT_PATH)
        else:
            _qdrant_client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    return _qdrant_client

def _embed(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    client = get_embed_client()
    try:
        embeddings: List[List[float]] = []
        for start in range(0, len(texts), settings.EMBED_BATCH_SIZE):
            batch = texts[start:start + settings.EMBED_BATCH_SIZE]
            response = client.embeddings.create(
                input=batch,
                model=settings.EMBED_MODEL_NAME,
                dimensions=settings.EMBED_DIMENSION,
            )
            batch_embeddings = [
                data.embedding
                for data in sorted(response.data, key=lambda item: item.index)
            ]
            if len(batch_embeddings) != len(batch):
                raise RuntimeError(
                    "Embedding provider returned "
                    f"{len(batch_embeddings)} vectors for {len(batch)} inputs"
                )
            invalid_dimensions = {
                len(vector)
                for vector in batch_embeddings
                if len(vector) != settings.EMBED_DIMENSION
            }
            if invalid_dimensions:
                raise RuntimeError(
                    "Embedding provider returned unexpected vector dimensions "
                    f"{sorted(invalid_dimensions)}; expected "
                    f"{settings.EMBED_DIMENSION}"
                )
            embeddings.extend(batch_embeddings)
        return embeddings
    except Exception as e:
        logger.error(f"Embedding API Error: {e}")
        raise


def _embed_query(question: str, request_id: str | None = None) -> List[float]:
    normalized = " ".join(question.casefold().split())
    cache_key = (
        settings.EMBED_MODEL_NAME,
        settings.EMBED_DIMENSION,
        normalized,
    )
    now = time.monotonic()
    with _query_embedding_cache_lock:
        cached = _query_embedding_cache.get(cache_key)
        if cached and now - cached[0] <= _QUERY_CACHE_TTL_SECONDS:
            _query_embedding_cache.move_to_end(cache_key)
            logger.info(json.dumps({
                "event": "chat_timing",
                "request_id": request_id or "-",
                "stage": "embedding",
                "elapsed_ms": 0,
                "cache_hit": True,
            }, ensure_ascii=False))
            return cached[1]
        if cached:
            _query_embedding_cache.pop(cache_key, None)

    started_at = time.perf_counter()
    try:
        vector = _embed([question])[0]
    except Exception:
        logger.info(json.dumps({
            "event": "chat_timing",
            "request_id": request_id or "-",
            "stage": "embedding",
            "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 2),
            "cache_hit": False,
            "failed": True,
        }, ensure_ascii=False))
        raise
    logger.info(json.dumps({
        "event": "chat_timing",
        "request_id": request_id or "-",
        "stage": "embedding",
        "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 2),
        "cache_hit": False,
    }, ensure_ascii=False))
    with _query_embedding_cache_lock:
        _query_embedding_cache[cache_key] = (now, vector)
        _query_embedding_cache.move_to_end(cache_key)
        while len(_query_embedding_cache) > _QUERY_CACHE_MAX_SIZE:
            _query_embedding_cache.popitem(last=False)
    return vector

def init_collection():
    global _collection_ready, _payload_index_checked
    if _collection_ready:
        return
    client = get_qdrant_client()
    collections = client.get_collections().collections
    exists = any(c.name == settings.QDRANT_COLLECTION_NAME for c in collections)

    if not exists:
        logger.info(f"创建 Qdrant 集合: {settings.QDRANT_COLLECTION_NAME}")
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=settings.EMBED_DIMENSION,
                distance=models.Distance.COSINE,
            ),
        )
    else:
        collection = client.get_collection(settings.QDRANT_COLLECTION_NAME)
        configured_size = getattr(collection.config.params.vectors, "size", None)
        if configured_size != settings.EMBED_DIMENSION:
            raise RuntimeError(
                f"Qdrant collection {settings.QDRANT_COLLECTION_NAME!r} uses "
                f"{configured_size} dimensions, but EMBED_DIMENSION is "
                f"{settings.EMBED_DIMENSION}. Stop the backend and rebuild "
                "the vector index."
            )
    if not _payload_index_checked:
        if settings.QDRANT_PATH:
            # QdrantLocal evaluates payload filters exactly but does not build
            # payload indexes. The server-mode branch below creates the index.
            logger.info("QdrantLocal 模式不支持 payload index，保留精确 scope_keys 过滤")
        else:
            collection = client.get_collection(settings.QDRANT_COLLECTION_NAME)
            if "scope_keys" not in (collection.payload_schema or {}):
                client.create_payload_index(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    field_name="scope_keys",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                    wait=True,
                )
        _payload_index_checked = True
    _collection_ready = True

def clear_collection() -> None:
    global _collection_ready, _payload_index_checked
    client = get_qdrant_client()
    collections = client.get_collections().collections
    exists = any(c.name == settings.QDRANT_COLLECTION_NAME for c in collections)
    if exists:
        logger.info(f"删除 Qdrant 集合: {settings.QDRANT_COLLECTION_NAME}")
        client.delete_collection(collection_name=settings.QDRANT_COLLECTION_NAME)
    _payload_index_checked = False
    _collection_ready = False
    init_collection()

def add_documents(chunks: List[Dict[str, Any]]) -> None:
    if not chunks:
        return

    init_collection()
    client = get_qdrant_client()

    texts = [c["text"] for c in chunks]
    embeddings = _embed(texts)

    points = []
    for i, chunk in enumerate(chunks):
        metadata = chunk.get("metadata", {})
        document_hash = metadata.get("document_hash", "")
        point_key = f"{document_hash}:{chunk.get('page', '')}:{i}:{chunk['text'][:80]}"
        # 统一元数据格式
        payload = {
            "text": chunk["text"],
            "source_file": chunk["source_file"],
            "source_type": chunk["source_type"],
            "chapter": chunk.get("chapter", ""),
            "page": str(chunk.get("page", "")),
            "document_hash": document_hash,
            "scope_keys": metadata.get("scope_keys", []),
            "sources": metadata.get("sources", []),
            "metadata": metadata # 额外元数据
        }

        points.append(models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, point_key)),
            vector=embeddings[i],
            payload=payload
        ))

    client.upsert(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        points=points
    )
    logger.info(f"成功向 Qdrant 写入 {len(points)} 条数据")


def _document_filter(content_hash: str) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key="document_hash",
                match=models.MatchValue(value=content_hash),
            )
        ]
    )


def update_document_access(
    content_hash: str,
    scope_keys: list[str],
    sources: list[dict],
) -> None:
    client = get_qdrant_client()
    client.set_payload(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        payload={
            "scope_keys": scope_keys,
            "sources": sources,
        },
        points=models.FilterSelector(filter=_document_filter(content_hash)),
    )


def delete_document(content_hash: str) -> None:
    client = get_qdrant_client()
    collections = client.get_collections().collections
    if not any(c.name == settings.QDRANT_COLLECTION_NAME for c in collections):
        return
    client.delete(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        points_selector=models.FilterSelector(
            filter=_document_filter(content_hash),
        ),
    )


def delete_material_documents(class_id: int, material_id: int) -> None:
    """按班级资料身份删除向量索引，避免误删其他班级的同名文件。"""
    client = get_qdrant_client()
    collections = client.get_collections().collections
    if not any(c.name == settings.QDRANT_COLLECTION_NAME for c in collections):
        return
    client.delete(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.class_id",
                        match=models.MatchValue(value=class_id),
                    ),
                    models.FieldCondition(
                        key="metadata.material_id",
                        match=models.MatchValue(value=material_id),
                    ),
                ]
            )
        ),
    )

def query(
    question: str,
    source_type: str = None,
    top_k: int = None,
    scope_keys: list[str] | None = None,
    request_id: str | None = None,
) -> List[Dict[str, Any]]:
    init_collection()
    client = get_qdrant_client()
    try:
        query_embedding = _embed_query(question, request_id=request_id)
    except Exception:
        logger.warning("查询向量生成失败，将由混合检索降级到 BM25")
        return []

    n_results = top_k if top_k is not None else settings.TOP_K

    # 构造过滤器
    must_conditions = []
    if source_type:
        must_conditions.append(
            models.FieldCondition(
                key="source_type",
                match=models.MatchValue(value=source_type)
            )
        )
    if scope_keys:
        must_conditions.append(
            models.FieldCondition(
                key="scope_keys",
                match=models.MatchAny(any=scope_keys),
            )
        )
    query_filter = models.Filter(must=must_conditions) if must_conditions else None

    qdrant_started_at = time.perf_counter()
    search_result = client.query_points(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        query=query_embedding,
        query_filter=query_filter,
        limit=n_results,
        with_payload=True
    )
    logger.info(json.dumps({
        "event": "chat_timing",
        "request_id": request_id or "-",
        "stage": "qdrant",
        "elapsed_ms": round((time.perf_counter() - qdrant_started_at) * 1000, 2),
        "result_count": len(search_result.points),
    }, ensure_ascii=False))

    output = []
    for hit in search_result.points:
        res = hit.payload
        res["similarity"] = round(hit.score, 3)
        output.append(res)

    return output
