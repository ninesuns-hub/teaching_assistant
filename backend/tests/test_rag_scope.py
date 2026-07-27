import os
import tempfile
import unittest

from agent_core.tools.knowledge_tools import create_knowledge_tool
from agent_core.rag.retriever import BM25Retriever
from app.core.data_manager import DataManager
from database import vector_repo
from qdrant_client import QdrantClient


class RagScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.retriever = BM25Retriever(
            os.path.join(self.temp_dir.name, "bm25.json")
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sha256_is_based_on_raw_file_bytes(self):
        content = b"discrete-math-course-material"
        self.assertEqual(
            DataManager.calculate_content_hash(content),
            "c813c3870cfbd72be8509af6aec9e97f8c9090bf509fc25688036f3a7eb27956",
        )

    def test_knowledge_tool_passes_class_context_to_searcher(self):
        captured = {}

        def query(question, class_id=None):
            captured["question"] = question
            captured["class_id"] = class_id
            return [{
                "source_file": "lecture.pdf",
                "page": "1",
                "text": "A theorem",
                "rrf_score": 0.1,
            }]

        tool = create_knowledge_tool(
            query,
            context_getter=lambda: {"class_id": 7},
        )
        output = tool.run("graph theorem")
        self.assertEqual(captured, {
            "question": "graph theorem",
            "class_id": 7,
        })
        self.assertIn("lecture.pdf", output)

    def test_query_only_uses_global_and_current_class(self):
        self.retriever.add_documents([
            {
                "text": "classoneonly theorem",
                "metadata": {
                    "document_hash": "class-1",
                    "scope_keys": ["class:1"],
                },
            },
            {
                "text": "classtwoonly theorem",
                "metadata": {
                    "document_hash": "class-2",
                    "scope_keys": ["class:2"],
                },
            },
            {
                "text": "globalonly theorem",
                "metadata": {
                    "document_hash": "global-1",
                    "scope_keys": ["global"],
                },
            },
            {
                "text": "anotherglobal theorem",
                "metadata": {
                    "document_hash": "global-2",
                    "scope_keys": ["global"],
                },
            },
        ])

        results = self.retriever.query(
            "classoneonly globalonly",
            top_k=10,
            scope_keys=["global", "class:1"],
        )
        hashes = {
            item["metadata"]["document_hash"] for item in results
        }
        self.assertEqual(hashes, {"class-1", "global-1"})
        self.assertNotIn("class-2", hashes)

    def test_same_hash_replaces_existing_bm25_chunks(self):
        self.retriever.add_documents([
            {
                "text": "old content",
                "metadata": {
                    "document_hash": "same-hash",
                    "scope_keys": ["global"],
                },
            }
        ])
        self.retriever.add_documents([
            {
                "text": "new content",
                "metadata": {
                    "document_hash": "same-hash",
                    "scope_keys": ["global", "class:1"],
                },
            }
        ])
        matching = [
            item for item in self.retriever.corpus
            if item["metadata"]["document_hash"] == "same-hash"
        ]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["text"], "new content")

    def test_bm25_scope_index_is_cached_and_pretokens_are_persisted(self):
        self.retriever.add_documents([
            {
                "text": "cached graph theorem",
                "metadata": {
                    "document_hash": "cached-hash",
                    "scope_keys": ["global", "class:1"],
                },
            }
        ])
        scopes = ["global", "class:1"]
        self.retriever.query("graph", scope_keys=scopes)
        cached_index = self.retriever._scope_cache[tuple(sorted(scopes))][1]
        self.retriever.query("theorem", scope_keys=scopes)
        self.assertIs(
            self.retriever._scope_cache[tuple(sorted(scopes))][1],
            cached_index,
        )

        reloaded = BM25Retriever(self.retriever.storage_path)
        self.assertEqual(len(reloaded._tokenized_corpus), 1)
        self.assertEqual(reloaded._tokenized_corpus[0], ["cached", " ", "graph", " ", "theorem"])

    def test_qdrant_scope_filter_and_access_update(self):
        original_client = vector_repo._qdrant_client
        original_embed = vector_repo._embed
        original_payload_index_checked = vector_repo._payload_index_checked
        original_collection_ready = vector_repo._collection_ready
        vector_repo._query_embedding_cache.clear()
        vector_repo._qdrant_client = QdrantClient(":memory:")
        vector_repo._payload_index_checked = False
        vector_repo._collection_ready = False
        vector_repo._embed = lambda texts: [
            [1.0] + [0.0] * 1535 for _ in texts
        ]
        try:
            vector_repo.add_documents([
                {
                    "text": "class one",
                    "source_file": "one.pdf",
                    "source_type": "pdf",
                    "page": 1,
                    "metadata": {
                        "document_hash": "qdrant-hash",
                        "scope_keys": ["class:1"],
                        "sources": [],
                    },
                }
            ])
            class_one = vector_repo.query(
                "question",
                top_k=5,
                scope_keys=["global", "class:1"],
            )
            self.assertEqual(
                [item["document_hash"] for item in class_one],
                ["qdrant-hash"],
            )

            vector_repo.update_document_access(
                "qdrant-hash",
                ["class:2"],
                [],
            )
            self.assertEqual(
                vector_repo.query(
                    "question",
                    top_k=5,
                    scope_keys=["global", "class:1"],
                ),
                [],
            )
            class_two = vector_repo.query(
                "question",
                top_k=5,
                scope_keys=["global", "class:2"],
            )
            self.assertEqual(
                [item["document_hash"] for item in class_two],
                ["qdrant-hash"],
            )
        finally:
            vector_repo._query_embedding_cache.clear()
            vector_repo._qdrant_client = original_client
            vector_repo._embed = original_embed
            vector_repo._payload_index_checked = original_payload_index_checked
            vector_repo._collection_ready = original_collection_ready


if __name__ == "__main__":
    unittest.main()
