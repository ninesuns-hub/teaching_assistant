import unittest
import json
from types import SimpleNamespace
from unittest.mock import patch

from agent_core.react_agent import AnswerStreamExtractor, ReactAgent
from agent_core.tools.base import Tool
from app.core.mermaid_service import repair_mermaid_source
from app.interfaces.api.schemas import MermaidRepairRequest


class AnswerStreamExtractorTests(unittest.TestCase):
    def test_extracts_only_answer_across_single_character_chunks(self):
        raw = (
            "<thought>private reasoning</thought>"
            "<answer>第一行\n\n```mermaid\ngraph LR\nA-->B\n```</answer>"
        )
        extractor = AnswerStreamExtractor()
        output = []
        for character in raw:
            output.extend(extractor.feed(character))
        output.extend(extractor.finish())
        self.assertEqual(
            "".join(output),
            "第一行\n\n```mermaid\ngraph LR\nA-->B\n```",
        )
        self.assertNotIn("private reasoning", "".join(output))
        self.assertNotIn("</answer>", "".join(output))

    def test_react_agent_keeps_tool_loop_and_streams_final_answer(self):
        config = SimpleNamespace(
            CHAT_API_KEY="test",
            CHAT_BASE_URL="https://example.invalid",
            CHAT_MODEL_NAME="test-model",
            MAX_TOKENS=256,
            SYSTEM_PROMPT="system",
        )
        tool = Tool(
            name="query_lecture_knowledge",
            func=lambda value: f"资料：{value}",
            description="knowledge",
        )
        agent = ReactAgent(config, [tool])
        responses = iter([
            [
                "<thought>需要检索</thought>",
                "<action>query_lecture_knowledge</action>",
                "<input>graph</input>",
            ],
            [
                "<thought>已经取得资料</thought><answer>",
                "这是",
                "答案",
                "</answer>",
            ],
        ])
        agent._call_llm_stream = lambda _prompt: iter(next(responses))

        events = list(agent.stream_events(
            "什么是图？",
            request_context={"request_id": "test-request", "class_id": 1},
        ))
        content = "".join(
            event.get("delta", "")
            for event in events
            if event["type"] == "content"
        )
        stages = [
            event["stage"] for event in events if event["type"] == "status"
        ]
        self.assertEqual(content, "这是答案")
        self.assertIn("retrieving", stages)
        self.assertIn("organizing", stages)
        self.assertNotIn("需要检索", content)

    def test_answer_delta_is_yielded_before_upstream_stream_finishes(self):
        config = SimpleNamespace(
            CHAT_API_KEY="test",
            CHAT_BASE_URL="https://example.invalid",
            CHAT_MODEL_NAME="test-model",
            MAX_TOKENS=256,
            SYSTEM_PROMPT="system",
        )
        agent = ReactAgent(config, [])
        state = {"upstream_resumed": False}

        def upstream(_prompt):
            yield "<answer>第一个片段"
            state["upstream_resumed"] = True
            yield "第二个片段</answer>"

        agent._call_llm_stream = upstream
        events = agent.stream_events(
            "测试流式",
            request_context={"request_id": "stream-test"},
        )
        self.assertEqual(next(events)["type"], "status")
        first_content = next(events)
        self.assertEqual(first_content, {"type": "content", "delta": "第一个片段"})
        self.assertFalse(state["upstream_resumed"])


class MermaidRepairServiceTests(unittest.TestCase):
    @patch("app.core.mermaid_service.OpenAI")
    def test_extracts_repaired_mermaid_fence(self, openai_mock):
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            "```mermaid\n"
                            'flowchart LR\nsubgraph safe_id["安全标题"]\nA-->B\nend\n'
                            "```"
                        )
                    )
                )
            ]
        )
        openai_mock.return_value.chat.completions.create.return_value = response
        repaired = repair_mermaid_source(
            "graph LR\nsubgraph 标题:a->b\nA-->B\nend",
            "parse error",
        )
        self.assertTrue(repaired.startswith("flowchart LR"))
        self.assertIn('safe_id["安全标题"]', repaired)
        self.assertNotIn("```", repaired)

    def test_repair_endpoint_rejects_source_outside_saved_message(self):
        from app.interfaces.api import routes

        payload = MermaidRepairRequest(
            conversation_id="conversation",
            message_id=10,
            source="graph LR\nX-->Y",
        )
        saved_message = SimpleNamespace(content="```mermaid\ngraph LR\nA-->B\n```")
        with patch.object(
            routes.conversation_repo,
            "get_user_assistant_message",
            return_value=saved_message,
        ):
            with self.assertRaisesRegex(Exception, "图表源码不属于"):
                routes.repair_mermaid(
                    payload,
                    current_user=SimpleNamespace(id=1),
                    db=SimpleNamespace(),
                )


class ChatSseTests(unittest.TestCase):
    def test_stream_persists_before_done_event(self):
        from app.interfaces.api import routes

        class FakeAgent:
            last_observations = []

            @staticmethod
            def stream_events(_agent_input, request_context=None):
                yield {"type": "status", "stage": "understanding"}
                yield {"type": "content", "delta": "第一段"}
                yield {"type": "content", "delta": "第二段"}

        fake_db = SimpleNamespace(close=lambda: None)
        persisted = []

        def add_message(_db, _conversation_id, role, content, **_kwargs):
            persisted.append((role, content))
            return SimpleNamespace(id=88)

        with (
            patch.object(routes, "agent", FakeAgent()),
            patch("database.mysql_db.SessionLocal", return_value=fake_db),
            patch.object(routes.conversation_repo, "add_message", side_effect=add_message),
        ):
            frames = list(routes._stream_and_persist(
                "问题",
                "问题",
                3,
                "public-id",
                {"request_id": "request-id"},
            ))

        self.assertEqual(
            persisted,
            [("user", "问题"), ("assistant", "第一段第二段")],
        )
        self.assertIn("event: status", frames[0])
        self.assertIn("event: content", frames[1])
        self.assertIn("event: done", frames[-1])
        done_payload = json.loads(
            next(
                line[5:].strip()
                for line in frames[-1].splitlines()
                if line.startswith("data:")
            )
        )
        self.assertEqual(done_payload["message_id"], 88)
        self.assertEqual(done_payload["conversation_id"], "public-id")


if __name__ == "__main__":
    unittest.main()
