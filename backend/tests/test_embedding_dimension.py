import unittest
from types import SimpleNamespace
from unittest.mock import patch

from qdrant_client import QdrantClient
from qdrant_client.http import models

from agent_core.config.settings import settings
from database import memory_vector_repo, vector_repo


class _FakeEmbeddings:
    def __init__(self, returned_dimension: int):
        self.returned_dimension = returned_dimension
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(data=[
            SimpleNamespace(
                index=index,
                embedding=[float(index)] + [0.0] * (self.returned_dimension - 1),
            )
            for index, _ in enumerate(kwargs["input"])
        ])


class EmbeddingDimensionTests(unittest.TestCase):
    def setUp(self):
        self.original_embed_client = vector_repo._embed_client
        self.original_qdrant_client = vector_repo._qdrant_client
        self.original_collection_ready = vector_repo._collection_ready
        self.original_payload_index_checked = vector_repo._payload_index_checked
        self.original_memory_ready = memory_vector_repo._ready

    def tearDown(self):
        vector_repo._embed_client = self.original_embed_client
        vector_repo._qdrant_client = self.original_qdrant_client
        vector_repo._collection_ready = self.original_collection_ready
        vector_repo._payload_index_checked = self.original_payload_index_checked
        memory_vector_repo._ready = self.original_memory_ready

    def test_embedding_request_uses_configured_dimension_and_batches(self):
        fake_embeddings = _FakeEmbeddings(returned_dimension=4096)
        vector_repo._embed_client = SimpleNamespace(embeddings=fake_embeddings)

        with (
            patch.object(settings, "EMBED_DIMENSION", 4096),
            patch.object(settings, "EMBED_BATCH_SIZE", 2),
        ):
            result = vector_repo._embed(["one", "two", "three"])

        self.assertEqual(len(result), 3)
        self.assertEqual([len(vector) for vector in result], [4096, 4096, 4096])
        self.assertEqual(
            [call["dimensions"] for call in fake_embeddings.calls],
            [4096, 4096],
        )
        self.assertEqual(
            [call["input"] for call in fake_embeddings.calls],
            [["one", "two"], ["three"]],
        )

    def test_embedding_response_with_wrong_dimension_is_rejected(self):
        fake_embeddings = _FakeEmbeddings(returned_dimension=1536)
        vector_repo._embed_client = SimpleNamespace(embeddings=fake_embeddings)

        with patch.object(settings, "EMBED_DIMENSION", 4096):
            with self.assertRaisesRegex(RuntimeError, "expected 4096"):
                vector_repo._embed(["one"])

    def test_existing_course_collection_dimension_must_match(self):
        client = QdrantClient(":memory:")
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=1536,
                distance=models.Distance.COSINE,
            ),
        )
        vector_repo._qdrant_client = client
        vector_repo._collection_ready = False
        vector_repo._payload_index_checked = False

        with patch.object(settings, "EMBED_DIMENSION", 4096):
            with self.assertRaisesRegex(RuntimeError, "rebuild the vector index"):
                vector_repo.init_collection()

    def test_existing_memory_collection_dimension_must_match(self):
        client = QdrantClient(":memory:")
        client.create_collection(
            collection_name=settings.QDRANT_MEMORY_COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=1536,
                distance=models.Distance.COSINE,
            ),
        )
        vector_repo._qdrant_client = client
        memory_vector_repo._ready = False

        with patch.object(settings, "EMBED_DIMENSION", 4096):
            with self.assertRaisesRegex(
                RuntimeError,
                "rebuild the memory vector index",
            ):
                memory_vector_repo.init_collection()


if __name__ == "__main__":
    unittest.main()
