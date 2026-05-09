import os
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import chromadb
from sentence_transformers import SentenceTransformer
from config import VECTOR_DB_PATH, TOP_K

# paraphrase-multilingual-MiniLM-L12-v2 支持中文，适合课程内容检索
_embed_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


def _get_collection():
    """获取（或创建）ChromaDB 集合，不绑定任何内置 embedding 函数。"""
    client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
    collection = client.get_or_create_collection(
        name="course_materials",
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def _embed(texts: list[str]) -> list[list[float]]:
    """
    用本地模型把文本列表转成向量列表。
    normalize_embeddings=True 保证向量长度为1，配合余弦相似度效果更好。
    """
    embeddings = _embed_model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()


def add_documents(chunks: list[dict]) -> None:
    """将文档片段批量存入向量数据库。"""
    if not chunks:
        return

    collection = _get_collection()

    ids       = [c["id"]   for c in chunks]
    texts     = [c["text"] for c in chunks]
    metadatas = [
        {
            "source_type": c["source_type"],
            "source_file": c["source_file"],
            "chapter":     c.get("chapter", ""),
            "page":        str(c.get("page", "")),
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
    print(f"[向量库] 已写入 {len(chunks)} 个片段")


def query(question: str, source_type: str = None) -> list[dict]:
    """根据问题语义检索最相关的文档片段。"""
    collection = _get_collection()

    question_embedding = _embed([question])[0]

    where = {"source_type": source_type} if source_type else None

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=TOP_K,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append({
            "text":        doc,
            "source_file": meta.get("source_file", ""),
            "source_type": meta.get("source_type", ""),
            "chapter":     meta.get("chapter", ""),
            "page":        meta.get("page", ""),
            "similarity":  round(1 - dist, 3),
        })

    return output


def get_stats() -> dict:
    """返回数据库当前状态。"""
    collection = _get_collection()
    total     = collection.count()
    ppt_count = collection.get(where={"source_type": "ppt"})
    pdf_count = collection.get(where={"source_type": "pdf"})
    return {
        "total":     total,
        "ppt_count": len(ppt_count["ids"]),
        "pdf_count": len(pdf_count["ids"]),
    }