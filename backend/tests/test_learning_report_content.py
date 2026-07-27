import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from agent_core.skills.class_feedback import generate_class_feedback
from agent_core.skills.student_report import generate_student_report


def _completion(payload):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=json.dumps(payload, ensure_ascii=False),
                )
            )
        ]
    )


class StudentReportContentTests(unittest.TestCase):
    def test_empty_report_keeps_student_and_teacher_suggestions_separate(self):
        result = generate_student_report("小明", "一班", [])

        self.assertNotIn("学习建议", result["summary"])
        self.assertEqual(
            result["stats"]["suggestions"],
            result["stats"]["student_suggestions"],
        )
        self.assertNotEqual(
            result["stats"]["student_suggestions"],
            result["stats"]["teaching_suggestions"],
        )

    @patch("agent_core.skills.student_report.OpenAI")
    def test_generated_report_strips_duplicate_advice_and_normalizes_stats(
        self,
        openai_mock,
    ):
        openai_mock.return_value.chat.completions.create.return_value = _completion({
            "summary_text": (
                "学习概况：\n掌握了基础概念。\n\n"
                "薄弱环节：\n证明步骤还不够熟练。\n\n"
                "学习建议：\n1. 继续练习。"
            ),
            "stats": {
                "topics": ["集合"],
                "weak_points": ["证明步骤"],
                "student_suggestions": ["你可以独立重写一次证明。"],
                "teaching_suggestions": ["教师可以安排一道同构证明题。"],
                "suggestions": ["模型返回的错误兼容内容"],
            },
        })

        result = generate_student_report(
            "小明",
            "一班",
            [{"role": "user", "content": "如何证明空集唯一？"}],
        )

        self.assertNotIn("学习建议", result["summary"])
        self.assertNotIn("继续练习", result["summary"])
        self.assertEqual(
            result["stats"]["suggestions"],
            ["你可以独立重写一次证明。"],
        )
        self.assertEqual(
            result["stats"]["teaching_suggestions"],
            ["教师可以安排一道同构证明题。"],
        )
        prompt = openai_mock.return_value.chat.completions.create.call_args.kwargs[
            "messages"
        ][1]["content"]
        self.assertIn("student_suggestions", prompt)
        self.assertIn("teaching_suggestions", prompt)
        self.assertIn("禁止出现「学习建议」「教学建议」", prompt)


class ClassFeedbackContentTests(unittest.TestCase):
    @patch("agent_core.skills.class_feedback.OpenAI")
    def test_class_feedback_keeps_advice_only_in_structured_stats(
        self,
        openai_mock,
    ):
        openai_mock.return_value.chat.completions.create.return_value = _completion({
            "summary_text": (
                "班级整体情况：\n基础概念掌握较好。\n\n"
                "教学建议：\n1. 增加例题。"
            ),
            "stats": {
                "common_topics": ["集合"],
                "class_weak_points": ["证明"],
                "teaching_suggestions": ["增加一组证明例题。"],
            },
        })

        result = generate_class_feedback(
            "一班",
            [{"student_name": "小明", "summary": "掌握基础概念"}],
            [{"student_name": "小明", "message_count": 3}],
        )

        self.assertNotIn("教学建议", result["summary"])
        self.assertNotIn("增加例题", result["summary"])
        self.assertEqual(
            result["stats"]["teaching_suggestions"],
            ["增加一组证明例题。"],
        )


if __name__ == "__main__":
    unittest.main()
