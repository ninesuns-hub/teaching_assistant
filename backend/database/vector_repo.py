import os
import uuid
import logging
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models
from openai import OpenAI
from agent_core.config.settings import settings

logger = logging.getLogger(__name__)

# 鈹€鈹€ OpenAI 瀹㈡埛绔?(涓撶敤 Embedding) 鈹€鈹€
_embed_client = None

def get_embed_client():
    global _embed_client
    if _embed_client is None:
        _embed_client = OpenAI(
            api_key=settings.EMBED_API_KEY,
            base_url=settings.EMBED_BASE_URL
        )
    return _embed_client

# 鈹€鈹€ Qdrant 瀹㈡埛绔?鈹€鈹€
_qdrant_client = None

def get_qdrant_client():
    global _qdrant_client
    if _qdrant_client is None:
        # 濡傛灉鎻愪緵浜?QDRANT_PATH锛屽垯浣跨敤鏈湴瀛樺偍妯″紡
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
        # 鍏滃簳锛氳繑鍥?1536 缁撮浂鍚戦噺 (text-embedding-3-small)
        return [[0.0] * 1536 for _ in texts]

def init_collection():
    client = get_qdrant_client()
    collections = client.get_collections().collections
    exists = any(c.name == settings.QDRANT_COLLECTION_NAME for c in collections)

    if not exists:
        logger.info(f"鍒涘缓 Qdrant 闆嗗悎: {settings.QDRANT_COLLECTION_NAME}")
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        )

def clear_collection() -> None:
    client = get_qdrant_client()
    collections = client.get_collections().collections
    exists = any(c.name == settings.QDRANT_COLLECTION_NAME for c in collections)
    if exists:
        logger.info(f"鍒犻櫎 Qdrant 闆嗗悎: {settings.QDRANT_COLLECTION_NAME}")
        client.delete_collection(collection_name=settings.QDRANT_COLLECTION_NAME)
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
        # 缁熶竴鍏冩暟鎹牸寮?
        payload = {
            "text": chunk["text"],
            "source_file": chunk["source_file"],
            "source_type": chunk["source_type"],
            "chapter": chunk.get("chapter", ""),
            "page": str(chunk.get("page", "")),
            "metadata": chunk.get("metadata", {}) # 棰濆鍏冩暟鎹?
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
    logger.info(f"鎴愬姛鍚?Qdrant 鍐欏叆 {len(points)} 鏉℃暟鎹?)

def query(question: str, source_type: str = None, top_k: int = None) -> List[Dict[str, Any]]:
    client = get_qdrant_client()
    embeddings = _embed([question])
    if not embeddings:
        return []

    n_results = top_k if top_k is not None else settings.TOP_K

    # 鏋勯€犺繃婊ゅ櫒
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
