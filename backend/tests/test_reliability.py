import json
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import MagicMock, patch

import httpx
import fitz
from openai import APIStatusError, APITimeoutError
from agent_core.react_agent import ReactAgent, ChatStreamError
from agent_core.math_diagrams import validate_diagram
from agent_core.vision_client import request_vision, VisionError
from app.core import auth_sessions


def chunk(content=None, finish=None):
    return NS(choices=[NS(delta=NS(content=content), finish_reason=finish)])


class ChatReliabilityTests(unittest.TestCase):
    def agent(self):
        return ReactAgent(NS(CHAT_API_KEY='test', CHAT_BASE_URL='https://example.invalid',
                             CHAT_MODEL_NAME='test', MAX_TOKENS=8192, CHAT_MAX_CONTINUATIONS=2,
                             SYSTEM_PROMPT='system'), [])

    def test_length_continues_same_answer_without_repeating_prefix(self):
        agent = self.agent()
        agent._client = MagicMock()
        agent._client.chat.completions.create.side_effect = [
            iter([chunk('<answer>这是完整回答的开头，公式为 $x'), chunk(finish='length')]),
            iter([chunk('这是完整回答的开头，公式为 $x+1$。</answer>'), chunk(finish='stop')]),
        ]
        events = list(agent.stream_events('测试', {'request_id': 'continuation'}))
        text = ''.join(e.get('delta', '') for e in events if e['type'] == 'content')
        self.assertEqual(text, '这是完整回答的开头，公式为 $x+1$。')
        self.assertTrue(any(e.get('stage') == 'continuing' for e in events))
        self.assertFalse(any(e['type'] == 'error' for e in events))
        self.assertEqual(agent._client.chat.completions.create.call_count, 2)

    def test_three_length_streams_fail_instead_of_reporting_success(self):
        agent = self.agent()
        agent._client = MagicMock()
        agent._client.chat.completions.create.side_effect = [
            iter([chunk('<answer>部分内容'), chunk(finish='length')]),
            iter([chunk('仍未完成'), chunk(finish='length')]),
            iter([chunk('再次截断'), chunk(finish='length')]),
        ]
        events = list(agent.stream_events('测试'))
        error = next(e for e in events if e['type'] == 'error')
        self.assertEqual(error['code'], 'ANSWER_TRUNCATED')
        self.assertEqual(agent._client.chat.completions.create.call_count, 3)

    def test_stream_without_terminal_finish_reason_fails(self):
        agent = self.agent()
        agent._client = MagicMock()
        agent._client.chat.completions.create.return_value = iter([chunk('<answer>partial')])
        self.assertTrue(any(e.get('code') == 'UPSTREAM_INCOMPLETE' for e in agent.stream_events('test')))

    def test_image_is_recognized_before_model_and_reused_for_tool(self):
        agent = self.agent()
        agent._call_llm_stream = lambda prompt: iter(['<answer>已看到四个顶点。</answer>'])
        with patch('agent_core.react_agent.analyze_uploaded_image', return_value='a b c d') as vision:
            events = list(agent.stream_events('看看图片', {'image_path': '1/example.png'}))
        vision.assert_called_once()
        self.assertEqual(events[1]['stage'], 'analyzing_image')
        self.assertIn('a b c d', agent.last_observations)

    def test_failed_image_is_not_sent_to_answer_model(self):
        agent = self.agent()
        agent._call_llm_stream = MagicMock()
        with patch('agent_core.react_agent.analyze_uploaded_image', side_effect=VisionError('VISION_MODEL', '视觉模型配置异常')):
            events = list(agent.stream_events('图片', {'image_path': '1/example.png'}))
        agent._call_llm_stream.assert_not_called()
        self.assertEqual(events[-1]['code'], 'VISION_MODEL')


class VisionReliabilityTests(unittest.TestCase):
    def test_actual_png_file_is_encoded_after_validation(self):
        from agent_core.skills.vision import analyze_uploaded_image
        document = fitz.open()
        page = document.new_page(width=100, height=100)
        page.insert_text((10, 40), 'a -> b')
        raw = page.get_pixmap().tobytes('png')
        document.close()
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / 'graph.png'
            image.write_bytes(raw)
            with patch('agent_core.skills.vision.request_vision', return_value='a -> b') as request:
                self.assertEqual(analyze_uploaded_image(str(image)), 'a -> b')
            self.assertTrue(request.call_args.args[0].startswith('data:image/png;base64,'))

    def call(self, outcomes):
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            result if isinstance(result, Exception) else iter([
                chunk(result.choices[0].message.content), chunk(finish=result.choices[0].finish_reason),
            ]) for result in outcomes
        ]
        factory = MagicMock()
        factory.return_value.__enter__.return_value = client
        settings_patch = patch.multiple('agent_core.vision_client.settings', VISION_MODEL_NAME='vision-test',
                                        VISION_API_KEY='test', VISION_BASE_URL='https://example.invalid')
        return client, factory, settings_patch

    def test_transient_timeout_retries_twice_and_closes_client(self):
        timeout = APITimeoutError(request=httpx.Request('POST', 'https://example.invalid'))
        success = NS(choices=[NS(message=NS(content='四个顶点'), finish_reason='stop')])
        client, factory, settings_patch = self.call([timeout, timeout, success])
        with settings_patch, patch('agent_core.vision_client.OpenAI', factory), patch('agent_core.vision_client.time.sleep'):
            self.assertEqual(request_vision('data:image/png;base64,abc', '识图'), '四个顶点')
        self.assertEqual(client.chat.completions.create.call_count, 3)
        self.assertEqual(factory.call_args.kwargs['max_retries'], 0)
        factory.return_value.__exit__.assert_called_once()

    def test_wrong_model_is_not_retried(self):
        error = APIStatusError('invalid model', response=httpx.Response(400, request=httpx.Request('POST', 'https://example.invalid')),
                               body={'code': 20012, 'message': 'Model does not exist'})
        client, factory, settings_patch = self.call([error])
        with settings_patch, patch('agent_core.vision_client.OpenAI', factory), self.assertRaises(VisionError) as raised:
            request_vision('data:image/png;base64,abc', '识图')
        self.assertEqual(raised.exception.code, 'VISION_MODEL')
        self.assertEqual(client.chat.completions.create.call_count, 1)

    def test_empty_or_truncated_vision_is_failure(self):
        for text, finish, code in [('', 'stop', 'VISION_EMPTY'), ('partial', 'length', 'VISION_TRUNCATED')]:
            _, factory, settings_patch = self.call([NS(choices=[NS(message=NS(content=text), finish_reason=finish)])])
            with settings_patch, patch('agent_core.vision_client.OpenAI', factory), self.assertRaises(VisionError) as raised:
                request_vision('data:image/png;base64,abc', '识图')
            self.assertEqual(raised.exception.code, code)


class SessionTests(unittest.TestCase):
    def test_session_has_idle_and_absolute_deadlines_and_read_never_renews(self):
        cache = MagicMock()
        with patch.object(auth_sessions.redis_client, 'client', cache), patch.object(auth_sessions.time, 'time', return_value=1000):
            session = auth_sessions.create_session('a@tongji.edu.cn')
            self.assertEqual(session['idle_expires_at'], 2800)
            self.assertLessEqual(session['expires_at'], 29800)
            cache.get.return_value = json.dumps(session)
            cache.reset_mock()
            self.assertEqual(auth_sessions.read_session(session['sid'], session['email']), session)
            cache.setex.assert_not_called()
            cache.eval.assert_not_called()

    def test_expired_session_cannot_be_read(self):
        raw = json.dumps({'email': 'a', 'expires_at': 99999, 'idle_expires_at': 1000})
        with patch.object(auth_sessions.redis_client.client, 'get', return_value=raw), patch.object(auth_sessions.time, 'time', return_value=1001):
            with self.assertRaises(ValueError): auth_sessions.read_session('id', 'a')

    def test_missing_session_is_not_resurrected_by_activity(self):
        with patch.object(auth_sessions.redis_client.client, 'eval', return_value=None):
            with self.assertRaises(ValueError): auth_sessions.touch_session('logged-out')


class MathematicalDiagramTests(unittest.TestCase):
    def test_directed_multigraph_allows_loops_and_parallel_edges(self):
        value = {'version': 1, 'kind': 'graph', 'directed': True,
                 'nodes': [{'id': x, 'label': x} for x in 'abcd'],
                 'edges': [{'from': a, 'to': b} for a, b in [('a','a'), ('a','b'), ('a','b'), ('a','d'), ('c','b'), ('d','c'), ('c','d')]]}
        self.assertEqual(len(validate_diagram(value)['edges']), 7)

    def test_invalid_endpoint_duplicate_node_and_cycle_are_rejected(self):
        for value in [
            {'version':1, 'kind':'graph','nodes':[{'id':'a','label':'a'}],'edges':[{'from':'a','to':'b'}]},
            {'version':1, 'kind':'graph','nodes':[{'id':'a','label':'a'},{'id':'a','label':'a'}],'edges':[]},
            {'version':1, 'kind':'hasse','nodes':[{'id':'a','label':'a'}],'edges':[{'from':'a','to':'a'}]},
        ]:
            with self.assertRaises(ValueError): validate_diagram(value)


if __name__ == '__main__': unittest.main()
