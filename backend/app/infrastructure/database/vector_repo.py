import os
import chromadb
from openai import OpenAI
from app.config.settings import settings

# 初始化 OpenAI 客户端用于远程 Embedding
_client = None

def get_openai_client():
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
    return _client


def _get_collection():
    client = chromadb.PersistentClient(path=settings.VECTOR_DB_PATH)
    return client.get_or_create_collection(
        name="course_materials",
        metadata={"hnsw:space": "cosine"},
    )


def _embed(texts: list[str]) -> list[list[float]]:
    """使用远程 API 获取文本向量"""
    client = get_openai_client()
    try:
        response = client.embeddings.create(
            input=texts,
            model=settings.EMBEDDING_MODEL_NAME
        )
        return [data.embedding for data in response.data]
    except Exception as e:
        print(f"Embedding API Error: {e}")
        # 如果失败，返回零向量作为占位（实际生产应有更好的重试机制）
        # 假设维度为 1536 (text-embedding-3-small 的默认维度)
        return [[0.0] * 1536 for _ in texts]


def add_documents(chunks: list[dict]) -> None:
    if not chunks:
        return

    collection = _get_collection()
    ids = [c["id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [
        {
            "source_type": c["source_type"],
            "source_file": c["source_file"],
            "chapter": c.get("chapter", ""),
            "page": str(c.get("page", "")),
        }
        for c in chunks
    ]

    embeddings = _embed(texts)
    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def query(question: str, source_type: str = None) -> list[dict]:
    collection = _get_collection()
    embeddings = _embed([question])
    if not embeddings:
        return []
    
    question_embedding = embeddings[0]
    where = {"source_type": source_type} if source_type else None

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=settings.TOP_K,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    if results and results["documents"]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append({
                "text": doc,
                "source_file": meta.get("source_file", ""),
                "source_type": meta.get("source_type", ""),
                "chapter": meta.get("chapter", ""),
                "page": meta.get("page", ""),
                "similarity": round(1 - dist, 3),
            })
    return output
