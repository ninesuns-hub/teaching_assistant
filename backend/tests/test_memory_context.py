import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agent_core.react_agent import ReactAgent
from app.services.context_service import build_chat_context
from database import conversation_repo, memory_repo
from database.mysql_db import (
    Base,
    ChatGenerationLock,
    ChatMessage,
    Conversation,
    ConversationSummary,
    MemoryEvidence,
    MemoryItem,
    MemoryJob,
    User,
    UserMemorySetting,
)


class MemoryContextTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        for table in (
            User.__table__,
            Conversation.__table__,
            ChatMessage.__table__,
            ConversationSummary.__table__,
            UserMemorySetting.__table__,
            MemoryItem.__table__,
            MemoryEvidence.__table__,
            MemoryJob.__table__,
            ChatGenerationLock.__table__,
        ):
            table.create(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.user = User(
            id=1,
            email="1234567@tongji.edu.cn",
            name="Student",
            hashed_password="x",
        )
        self.conversation = Conversation(id=1, user_id=1, title="test")
        self.db.add_all([self.user, self.conversation])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_message_listing_returns_latest_window_in_chronological_order(self):
        for index in range(205):
            self.db.add(ChatMessage(
                conversation_id=1,
                role="user" if index % 2 == 0 else "assistant",
                content=f"message-{index}",
            ))
        self.db.commit()
        messages = conversation_repo.list_messages(self.db, 1, limit=200)
        self.assertEqual(messages[0].content, "message-5")
        self.assertEqual(messages[-1].content, "message-204")

    def test_context_excludes_current_message_and_keeps_recent_image(self):
        first = conversation_repo.add_message(
            self.db, 1, "user", "Explain graphs", image_path="1/graph.png"
        )
        conversation_repo.add_message(self.db, 1, "assistant", "A graph has vertices.")
        current = conversation_repo.add_message(self.db, 1, "user", "What about this?")
        with patch("app.services.context_service.settings.MEMORY_READ_ENABLED", False):
            context = build_chat_context(
                self.db,
                user_id=1,
                conversation_id=1,
                class_id=None,
                before_message_id=current.id,
                request_id="request",
                question=current.content,
            )
        self.assertEqual([item["content"] for item in context.history_messages], [
            "Explain graphs",
            "A graph has vertices.",
        ])
        self.assertEqual(context.recent_image_path, "1/graph.png")
        self.assertNotIn("What about this?", [item["content"] for item in context.history_messages])

    def test_memory_is_off_by_default(self):
        setting = memory_repo.get_or_create_setting(self.db, 1)
        self.assertFalse(setting.enabled)

    def test_vector_failure_falls_back_to_sql_memory(self):
        setting = memory_repo.get_or_create_setting(self.db, 1)
        setting.enabled = True
        self.db.add(MemoryItem(
            public_id="memory-1",
            user_id=1,
            class_id=None,
            memory_type="communication_preference",
            content="Explain with diagrams first",
            normalized_key="explanation_format",
            confidence=0.9,
            importance=0.9,
        ))
        current = conversation_repo.add_message(self.db, 1, "user", "Explain this graph")
        self.db.commit()
        with (
            patch("app.services.context_service.settings.MEMORY_READ_ENABLED", True),
            patch(
                "app.services.context_service.memory_vector_repo.query_memories",
                side_effect=RuntimeError("embedding unavailable"),
            ),
        ):
            context = build_chat_context(
                self.db,
                user_id=1,
                conversation_id=1,
                class_id=None,
                before_message_id=current.id,
                request_id="fallback",
                question=current.content,
            )
        self.assertEqual(context.memories, ["Explain with diagrams first"])

    def test_generation_lock_is_scoped_to_conversation(self):
        self.assertTrue(conversation_repo.acquire_generation_lock(self.db, 1, "request-a"))
        self.assertFalse(conversation_repo.acquire_generation_lock(self.db, 1, "request-b"))
        conversation_repo.release_generation_lock(self.db, 1, "request-a")
        self.assertTrue(conversation_repo.acquire_generation_lock(self.db, 1, "request-b"))

    def test_deleting_only_evidence_tombstones_derived_memory(self):
        message = conversation_repo.add_message(self.db, 1, "user", "I prefer diagrams")
        memory, _ = memory_repo.upsert_memory(
            self.db,
            user_id=1,
            class_id=None,
            memory_type="communication_preference",
            content="Prefer explanations with diagrams",
            confidence=0.9,
            importance=0.8,
            conversation_id=1,
            message_id=message.id,
            evidence_excerpt=message.content,
            normalized_key="explanation_format",
        )
        self.db.commit()
        deleted, vector_ids = conversation_repo.delete_conversation(
            self.db, self.conversation.public_id, 1
        )
        self.assertTrue(deleted)
        self.assertIn(memory.public_id, vector_ids)
        stored = self.db.query(MemoryItem).filter(MemoryItem.id == memory.id).first()
        self.assertEqual(stored.status, "deleted")


class AgentHistoryTests(unittest.TestCase):
    def test_history_is_forwarded_without_changing_react_protocol(self):
        config = SimpleNamespace(
            CHAT_API_KEY="test",
            CHAT_BASE_URL="https://example.invalid",
            CHAT_MODEL_NAME="test-model",
            MAX_TOKENS=256,
            SYSTEM_PROMPT="system",
        )
        agent = ReactAgent(config, [])
        captured = {}

        def stream(prompt, **kwargs):
            captured["prompt"] = prompt
            captured.update(kwargs)
            yield "<answer>connected answer</answer>"

        agent._call_llm_stream = stream
        events = list(agent.stream_events(
            "What about circuits?",
            request_context={
                "request_id": "history",
                "history_messages": [
                    {"role": "user", "content": "What is an Euler trail?"},
                    {"role": "assistant", "content": "It uses every edge once."},
                ],
                "summary_text": "The user is comparing Euler concepts.",
            },
        ))
        answer = "".join(
            event.get("delta", "") for event in events if event["type"] == "content"
        )
        self.assertEqual(answer, "connected answer")
        self.assertEqual(len(captured["history_messages"]), 2)
        self.assertIn("Euler", captured["summary_text"])
        self.assertIn("<answer>", captured["prompt"])


if __name__ == "__main__":
    unittest.main()
