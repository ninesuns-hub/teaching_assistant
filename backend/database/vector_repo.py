import os
import uuid
import logging
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models
from openai import OpenAI
from agent_core.config.settings import settings

logger = logging.getLogger(__name__)

# ── OpenAI 客户端 (专用 Embedding) ──
_embed_client = None

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
    client = get_embed_client()
    try:
        response = client.embeddings.create(
            input=texts,
            model=settings.EMBED_MODEL_NAME
        )
        return [data.embedding for data in response.data]
    except Exception as e:
        logger.error(f"Embedding API Error: {e}")
        # 兜底：返回 1536 维零向量 (text-embedding-3-small)
        return [[0.0] * 1536 for _ in texts]

def init_collection():
    client = get_qdrant_client()
    collections = client.get_collections().collections
    exists = any(c.name == settings.QDRANT_COLLECTION_NAME for c in collections)
    
    if not exists:
        logger.info(f"创建 Qdrant 集合: {settings.QDRANT_COLLECTION_NAME}")
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        )

def add_documents(chunks: List[Dict[str, Any]]) -> None:
    if not chunks:
        return

    init_collection()
    client = get_qdrant_client()
    
    texts = [c["text"] for c in chunks]
    embeddings = _embed(texts)
    
    points = []
    for i, chunk in enumerate(chunks):
        # 统一元数据格式
        payload = {
            "text": chunk["text"],
            "source_file": chunk["source_file"],
            "source_type": chunk["source_type"],
            "chapter": chunk.get("chapter", ""),
            "page": str(chunk.get("page", "")),
            "metadata": chunk.get("metadata", {}) # 额外元数据
        }
        
        points.append(models.PointStruct(
            id=str(uuid.uuid4()),
            vector=embeddings[i],
            payload=payload
        ))

    client.upsert(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        points=points
    )
    logger.info(f"成功向 Qdrant 写入 {len(points)} 条数据")

def query(question: str, source_type: str = None, top_k: int = None) -> List[Dict[str, Any]]:
    client = get_qdrant_client()
    embeddings = _embed([question])
    if not embeddings:
        return []
    
    n_results = top_k if top_k is not None else settings.TOP_K
    
    # 构造过滤器
    query_filter = None
    if source_type:
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="source_type",
                    match=models.MatchValue(value=source_type)
                )
            ]
        )

    search_result = client.query_points(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        query=embeddings[0],
        query_filter=query_filter,
        limit=n_results,
        with_payload=True
    )

    output = []
    for hit in search_result.points:
        res = hit.payload
        res["similarity"] = round(hit.score, 3)
        output.append(res)
        
    return output
