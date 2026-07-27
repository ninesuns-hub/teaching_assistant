import unittest
import json
from types import SimpleNamespace
from unittest.mock import patch

from agent_core.react_agent import AnswerStreamExtractor, ReactAgent
from agent_core.tools.base import Tool
from agent_core.visualization import decide_visualization
from app.core.mermaid_service import (
    MermaidSourceConflict,
    repair_mermaid_source,
    replace_saved_mermaid_source,
)
from app.interfaces.api.schemas import (
    MermaidRepairCommitRequest,
    MermaidRepairRequest,
)
from scripts.evaluate_chat_performance import validate_mermaid_sources


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
            "什么是集合的基数？",
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


class ProactiveVisualizationTests(unittest.TestCase):
    def test_balanced_visualization_policy(self):
        required = [
            "什么是图？",
            "离散数学中的树是什么？",
            "二叉树是什么？",
            "怎样判断二元关系是否具有传递性？",
            "欧拉回路和哈密顿回路有什么区别？",
            "请画图帮助证明这个关系具有传递性。",
            "Explain injective and surjective functions.",
        ]
        optional = [
            "请证明每棵树至少有两个叶节点。",
            "图论安排在第几周学习？",
            "请用纯文字解释二元关系。",
            "证明空集是唯一的。",
        ]
        for question in required:
            with self.subTest(question=question):
                self.assertTrue(decide_visualization(question).required)
        for question in optional:
            with self.subTest(question=question):
                self.assertFalse(decide_visualization(question).required)

    def test_missing_visual_is_supplemented_after_streamed_answer(self):
        config = SimpleNamespace(
            CHAT_API_KEY="test",
            CHAT_BASE_URL="https://example.invalid",
            CHAT_MODEL_NAME="test-model",
            MAX_TOKENS=256,
            SYSTEM_PROMPT="system",
        )
        agent = ReactAgent(config, [])
        agent._call_llm_stream = lambda _prompt: iter([
            "<answer>二叉树每个节点最多有两个孩子。</answer>",
        ])
        agent._generate_visual_supplement = lambda _question, _answer: (
            "\n\n### 图示示例\n\n```mermaid\nflowchart TB\nA-->B\n```"
        )

        events = list(agent.stream_events(
            "二叉树是什么？",
            request_context={"request_id": "visual-test"},
        ))
        content = "".join(
            event.get("delta", "")
            for event in events
            if event["type"] == "content"
        )
        stages = [
            event["stage"] for event in events if event["type"] == "status"
        ]

        self.assertTrue(content.startswith("二叉树每个节点"))
        self.assertIn("```mermaid", content)
        self.assertIn("generating_visual", stages)
        self.assertTrue(agent.request_context["visual_supplement_used"])

    def test_existing_visual_is_not_duplicated(self):
        config = SimpleNamespace(
            CHAT_API_KEY="test",
            CHAT_BASE_URL="https://example.invalid",
            CHAT_MODEL_NAME="test-model",
            MAX_TOKENS=256,
            SYSTEM_PROMPT="system",
        )
        agent = ReactAgent(config, [])
        agent._call_llm_stream = lambda _prompt: iter([
            "<answer>示例：\n```mermaid\nflowchart TB\nA-->B\n```</answer>",
        ])
        agent._generate_visual_supplement = lambda *_args: self.fail(
            "existing Mermaid must not trigger a supplement"
        )

        events = list(agent.stream_events(
            "二叉树是什么？",
            request_context={"request_id": "visual-existing"},
        ))
        content = "".join(
            event.get("delta", "")
            for event in events
            if event["type"] == "content"
        )

        self.assertEqual(content.lower().count("```mermaid"), 1)
        self.assertFalse(agent.request_context["visual_supplement_used"])

    def test_welcome_message_does_not_trigger_visual_supplement(self):
        config = SimpleNamespace(
            CHAT_API_KEY="test",
            CHAT_BASE_URL="https://example.invalid",
            CHAT_MODEL_NAME="test-model",
            MAX_TOKENS=256,
            SYSTEM_PROMPT="system",
        )
        agent = ReactAgent(config, [])
        agent._call_llm_stream = lambda _prompt: iter([
            "<answer>你好，我可以通过文字、公式和 Mermaid 图形帮助你学习。</answer>",
        ])
        agent._generate_visual_supplement = lambda *_args: self.fail(
            "welcome messages must not trigger a supplement"
        )

        events = list(agent.stream_events(
            "请介绍一下你自己",
            request_context={"request_id": "welcome-test", "welcome": True},
        ))

        self.assertFalse(any(
            event.get("stage") == "generating_visual" for event in events
        ))
        self.assertEqual(agent.request_context["visualization_reason"], "welcome")
        self.assertFalse(agent.request_context["visual_supplement_used"])

    def test_benchmark_uses_current_mermaid_parser(self):
        valid = validate_mermaid_sources(
            "```mermaid\nflowchart TB\nA-->B\n```"
        )
        invalid = validate_mermaid_sources(
            "```mermaid\nflowchart TB\nbroken[\n```"
        )
        suspicious = validate_mermaid_sources(
            '```mermaid\nflowchart TB\nA["땅듐"]\n```'
        )

        self.assertTrue(valid["validator_available"])
        self.assertEqual(valid["valid"], 1)
        self.assertEqual(invalid["invalid"], 1)
        self.assertEqual(suspicious["suspicious_text"], 1)


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

    def test_replaces_only_the_matching_mermaid_block(self):
        original = "graph LR\nA-->B"
        repaired = 'flowchart LR\nA["开始"] --> B["结束"]'
        content = (
            "保留这段正文。\n\n"
            f"```mermaid\n{original}\n```\n\n"
            "```mermaid\nflowchart TB\nX-->Y\n```\n"
        )

        updated, changed = replace_saved_mermaid_source(
            content,
            original,
            repaired,
        )

        self.assertTrue(changed)
        self.assertIn("保留这段正文。", updated)
        self.assertIn(repaired, updated)
        self.assertIn("flowchart TB\nX-->Y", updated)
        self.assertNotIn(original, updated)

    def test_repair_commit_is_idempotent(self):
        repaired = 'flowchart LR\nA["开始"] --> B["结束"]'
        content = f"```mermaid\n{repaired}\n```"

        updated, changed = replace_saved_mermaid_source(
            content,
            "graph LR\nA-->B",
            repaired,
        )

        self.assertFalse(changed)
        self.assertEqual(updated, content)

    def test_rejects_ambiguous_duplicate_mermaid_blocks(self):
        original = "graph LR\nA-->B"
        content = (
            f"```mermaid\n{original}\n```\n"
            f"```mermaid\n{original}\n```"
        )

        with self.assertRaisesRegex(MermaidSourceConflict, "多个相同图表"):
            replace_saved_mermaid_source(
                content,
                original,
                "flowchart LR\nA-->B",
            )

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

    def test_commit_endpoint_updates_original_message_content(self):
        from app.interfaces.api import routes

        original = "graph LR\nA-->B"
        repaired = 'flowchart LR\nA["开始"] --> B["结束"]'
        conversation = SimpleNamespace(updated_at=None)
        message = SimpleNamespace(
            content=f"正文\n```mermaid\n{original}\n```\n结尾",
            conversation=conversation,
        )

        class FakeDb:
            committed = False
            refreshed = False

            def commit(self):
                self.committed = True

            def refresh(self, _message):
                self.refreshed = True

            def rollback(self):
                raise AssertionError("successful commit must not roll back")

        db = FakeDb()
        payload = MermaidRepairCommitRequest(
            conversation_id="conversation",
            message_id=10,
            original_source=original,
            repaired_source=repaired,
        )
        with patch.object(
            routes.conversation_repo,
            "get_user_assistant_message_for_update",
            return_value=message,
        ):
            response = routes.commit_mermaid_repair(
                payload,
                current_user=SimpleNamespace(id=1),
                db=db,
            )

        self.assertTrue(db.committed)
        self.assertTrue(db.refreshed)
        self.assertEqual(response.content, message.content)
        self.assertIn("正文", response.content)
        self.assertIn("结尾", response.content)
        self.assertIn(repaired, response.content)
        self.assertNotIn(original, response.content)
        self.assertIsNotNone(conversation.updated_at)


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
