"""Integration tests for the local web GUI FastAPI server.

These tests exercise the JSON endpoints against a real :class:`AgentState`
without booting uvicorn, using ``fastapi.testclient.TestClient``.  Slash
commands are dispatched locally inside :class:`LocalCodingAgent` and never
hit the network, so the chat endpoint can be exercised end-to-end against
``/help``.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.gui.server import AgentState, create_app


def _build_client(tmp: Path) -> tuple[TestClient, AgentState]:
    state = AgentState(
        cwd=tmp,
        model='test-model',
        base_url='http://127.0.0.1:8000/v1',
        api_key='local-token',
        allow_shell=False,
        allow_write=False,
        session_directory=tmp / 'sessions',
    )
    return TestClient(create_app(state)), state


class GuiServerTests(unittest.TestCase):
    def test_root_serves_html(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            response = client.get('/')
            self.assertEqual(response.status_code, 200)
            self.assertIn('Claw Code', response.text)

    def test_static_assets_served(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            self.assertEqual(client.get('/static/app.css').status_code, 200)
            self.assertEqual(client.get('/static/app.js').status_code, 200)

    def test_state_snapshot_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            response = client.get('/api/state')
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload['model'], 'test-model')
            self.assertFalse(payload['allow_shell'])

            updated = client.post(
                '/api/state',
                json={'allow_shell': True, 'model': 'other-model'},
            )
            self.assertEqual(updated.status_code, 200)
            data = updated.json()
            self.assertTrue(data['allow_shell'])
            self.assertEqual(data['model'], 'other-model')

    def test_state_snapshot_exposes_runtime_knobs(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            payload = client.get('/api/state').json()
            # Defaults match AgentState's defaults — keeps the form populatable.
            self.assertEqual(payload['temperature'], 0.0)
            self.assertEqual(payload['timeout_seconds'], 120.0)
            self.assertFalse(payload['stream_model_responses'])
            self.assertEqual(payload['max_turns'], 12)

    def test_state_update_round_trips_runtime_knobs(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            updated = client.post(
                '/api/state',
                json={
                    'temperature': 0.7,
                    'timeout_seconds': 45.0,
                    'stream_model_responses': True,
                    'max_turns': 25,
                },
            )
            self.assertEqual(updated.status_code, 200)
            data = updated.json()
            self.assertEqual(data['temperature'], 0.7)
            self.assertEqual(data['timeout_seconds'], 45.0)
            self.assertTrue(data['stream_model_responses'])
            self.assertEqual(data['max_turns'], 25)

    def test_state_snapshot_defaults_budgets_to_null(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            payload = client.get('/api/state').json()
            for name in (
                'max_total_tokens',
                'max_input_tokens',
                'max_output_tokens',
                'max_reasoning_tokens',
                'max_total_cost_usd',
                'max_tool_calls',
                'max_delegated_tasks',
                'max_model_calls',
                'max_session_turns',
            ):
                self.assertIsNone(payload[name])

    def test_state_update_round_trips_and_clears_budgets(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            set_payload = {
                'max_total_tokens': 4096,
                'max_total_cost_usd': 5.50,
                'max_tool_calls': 20,
            }
            data = client.post('/api/state', json=set_payload).json()
            self.assertEqual(data['max_total_tokens'], 4096)
            self.assertEqual(data['max_total_cost_usd'], 5.50)
            self.assertEqual(data['max_tool_calls'], 20)
            # Untouched knobs stayed null.
            self.assertIsNone(data['max_output_tokens'])

            # Explicit null clears one knob but leaves the others alone.
            cleared = client.post(
                '/api/state',
                json={'max_tool_calls': None},
            ).json()
            self.assertIsNone(cleared['max_tool_calls'])
            self.assertEqual(cleared['max_total_tokens'], 4096)

    def test_state_update_rejects_nonpositive_budget(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            r = client.post('/api/state', json={'max_total_tokens': 0})
            self.assertEqual(r.status_code, 400)
            r = client.post('/api/state', json={'max_total_cost_usd': -1})
            self.assertEqual(r.status_code, 400)

    def test_state_round_trips_system_prompt_and_schema(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            payload = client.get('/api/state').json()
            self.assertIsNone(payload['custom_system_prompt'])
            self.assertIsNone(payload['response_schema'])
            self.assertEqual(payload['response_schema_name'], 'response')

            updated = client.post(
                '/api/state',
                json={
                    'custom_system_prompt': 'You are a focused refactor assistant.',
                    'append_system_prompt': '\n\nAlways quote line numbers.',
                    'response_schema': {
                        'type': 'object',
                        'properties': {'verdict': {'type': 'string'}},
                    },
                    'response_schema_name': 'verdict_object',
                    'response_schema_strict': True,
                },
            ).json()
            self.assertIn('focused refactor', updated['custom_system_prompt'])
            self.assertEqual(
                updated['response_schema'],
                {'type': 'object', 'properties': {'verdict': {'type': 'string'}}},
            )
            self.assertEqual(updated['response_schema_name'], 'verdict_object')
            self.assertTrue(updated['response_schema_strict'])

            # Empty string clears the system-prompt slot back to default.
            cleared = client.post(
                '/api/state',
                json={'custom_system_prompt': '', 'response_schema': None},
            ).json()
            self.assertIsNone(cleared['custom_system_prompt'])
            self.assertIsNone(cleared['response_schema'])

    def test_state_round_trips_context_knobs(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            extra = Path(d) / 'sibling'
            extra.mkdir()

            payload = client.get('/api/state').json()
            self.assertIsNone(payload['auto_snip_threshold_tokens'])
            self.assertEqual(payload['compact_preserve_messages'], 4)
            self.assertFalse(payload['disable_claude_md_discovery'])
            self.assertEqual(payload['additional_working_directories'], [])

            updated = client.post(
                '/api/state',
                json={
                    'auto_snip_threshold_tokens': 32000,
                    'auto_compact_threshold_tokens': 50000,
                    'compact_preserve_messages': 8,
                    'disable_claude_md_discovery': True,
                    'additional_working_directories': [str(extra)],
                },
            ).json()
            self.assertEqual(updated['auto_snip_threshold_tokens'], 32000)
            self.assertEqual(updated['auto_compact_threshold_tokens'], 50000)
            self.assertEqual(updated['compact_preserve_messages'], 8)
            self.assertTrue(updated['disable_claude_md_discovery'])
            self.assertEqual(
                updated['additional_working_directories'], [str(extra.resolve())]
            )

            cleared = client.post(
                '/api/state',
                json={
                    'auto_snip_threshold_tokens': None,
                    'additional_working_directories': [],
                },
            ).json()
            self.assertIsNone(cleared['auto_snip_threshold_tokens'])
            self.assertEqual(cleared['additional_working_directories'], [])
            # Other knobs untouched.
            self.assertEqual(cleared['auto_compact_threshold_tokens'], 50000)

    def test_state_rejects_missing_additional_working_dir(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            r = client.post(
                '/api/state',
                json={'additional_working_directories': [str(Path(d) / 'nope')]},
            )
            self.assertEqual(r.status_code, 400)

    def test_state_update_rejects_invalid_schema_payload(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            # Pydantic catches the type mismatch before our validator does.
            r = client.post('/api/state', json={'response_schema': 'not-an-object'})
            self.assertEqual(r.status_code, 422)

    def test_state_update_rejects_bad_runtime_knobs(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            # Negative temperature should be rejected with a 400.
            r = client.post('/api/state', json={'temperature': -0.1})
            self.assertEqual(r.status_code, 400)
            # Zero timeout should be rejected too — would hang a turn.
            r = client.post('/api/state', json={'timeout_seconds': 0})
            self.assertEqual(r.status_code, 400)
            # max_turns must be >= 1.
            r = client.post('/api/state', json={'max_turns': 0})
            self.assertEqual(r.status_code, 400)

    def test_state_update_rejects_missing_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            response = client.post(
                '/api/state',
                json={'cwd': str(Path(d) / 'does-not-exist')},
            )
            self.assertEqual(response.status_code, 400)

    def test_slash_commands_listed(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            response = client.get('/api/slash-commands')
            self.assertEqual(response.status_code, 200)
            commands = response.json()
            self.assertTrue(commands)
            primaries = {entry['primary'] for entry in commands}
            self.assertIn('help', primaries)

    def test_skills_listed(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            response = client.get('/api/skills')
            self.assertEqual(response.status_code, 200)
            skills = response.json()
            self.assertTrue(skills)
            names = {entry['name'] for entry in skills}
            self.assertIn('simplify', names)
            # Default response is user-invocable only.
            self.assertTrue(all(entry['user_invocable'] for entry in skills))

    def test_skills_can_include_internal(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            user_only = client.get('/api/skills').json()
            with_internal = client.get('/api/skills?include_internal=true').json()
            # `include_internal=true` returns at least as many entries.
            self.assertGreaterEqual(len(with_internal), len(user_only))

    def test_chat_runs_local_slash_command(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            response = client.post('/api/chat', json={'prompt': '/help'})
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload['turns'], 0)
            self.assertEqual(payload['tool_calls'], 0)
            self.assertIn('slash commands', payload['final_output'].lower())
            self.assertIn('/help', payload['final_output'])
            self.assertIn('total_tokens', payload['usage'])

    def test_chat_expands_pasted_contents_before_dispatch(self) -> None:
        # Capture the prompt that actually reaches LocalCodingAgent.run so the
        # test discriminates between "expansion happened" and "the field was
        # silently dropped".  Slash commands wouldn't observe the difference,
        # so we monkey-patch run() to short-circuit.
        captured: list[str] = []

        from src.agent_types import AgentRunResult, UsageStats

        with tempfile.TemporaryDirectory() as d:
            client, state = _build_client(Path(d))

            def fake_run(prompt: str, **kwargs: object) -> AgentRunResult:
                captured.append(prompt)
                return AgentRunResult(
                    final_output='ok',
                    turns=1,
                    tool_calls=0,
                    transcript=[{'role': 'user', 'content': prompt}],
                    session_id='sess-paste-test',
                    usage=UsageStats(),
                    total_cost_usd=0.0,
                    stop_reason='stop',
                )

            state.agent.run = fake_run  # type: ignore[assignment]
            response = client.post(
                '/api/chat',
                json={
                    'prompt': 'before [Pasted text #1] after',
                    'pasted_contents': {
                        '1': {'type': 'text', 'content': 'EXPANDED_BLOB'},
                    },
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(captured, ['before EXPANDED_BLOB after'])

    def test_chat_rejects_blank_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            response = client.post('/api/chat', json={'prompt': '   '})
            self.assertEqual(response.status_code, 400)

    def test_chat_resume_unknown_session_returns_404(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            response = client.post(
                '/api/chat',
                json={'prompt': '/help', 'resume_session_id': 'missing'},
            )
            self.assertEqual(response.status_code, 404)

    def test_sessions_list_empty_when_directory_absent(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            response = client.get('/api/sessions')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])

    def test_session_detail_404_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            response = client.get('/api/sessions/nope')
            self.assertEqual(response.status_code, 404)

    def test_clear_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _build_client(Path(d))
            response = client.post('/api/clear')
            self.assertEqual(response.status_code, 200)
            self.assertIn('model', response.json())

    def test_file_history_aggregates_across_sessions(self) -> None:
        import json

        with tempfile.TemporaryDirectory() as d:
            client, state = _build_client(Path(d))
            sess_dir = state.session_directory
            sess_dir.mkdir(parents=True, exist_ok=True)

            # Two saved sessions, each with one file_history entry — newest
            # entry should land first in the aggregated response.
            (sess_dir / 'older.json').write_text(json.dumps({
                'session_id': 'older',
                'turns': 1,
                'tool_calls': 1,
                'messages': [],
                'file_history': [
                    {
                        'timestamp': '2026-01-01T00:00:00+00:00',
                        'tool_name': 'Edit',
                        'history_kind': 'file_change',
                        'changed_paths': ['a.py'],
                    }
                ],
            }))
            (sess_dir / 'newer.json').write_text(json.dumps({
                'session_id': 'newer',
                'turns': 1,
                'tool_calls': 1,
                'messages': [],
                'file_history': [
                    {
                        'timestamp': '2026-04-22T00:00:00+00:00',
                        'tool_name': 'Write',
                        'history_kind': 'file_change',
                        'changed_paths': ['b.py'],
                    }
                ],
            }))

            payload = client.get('/api/file-history').json()
            self.assertEqual(payload['total'], 2)
            self.assertEqual(payload['entries'][0]['session_id'], 'newer')
            self.assertEqual(payload['entries'][0]['changed_paths'], ['b.py'])
            self.assertEqual(payload['entries'][1]['session_id'], 'older')

    def test_file_history_limit_caps_response(self) -> None:
        import json

        with tempfile.TemporaryDirectory() as d:
            client, state = _build_client(Path(d))
            sess_dir = state.session_directory
            sess_dir.mkdir(parents=True, exist_ok=True)
            entries = [
                {'timestamp': f'2026-04-22T00:00:{i:02d}+00:00', 'tool_name': 'Edit'}
                for i in range(10)
            ]
            (sess_dir / 's.json').write_text(json.dumps({
                'session_id': 's', 'turns': 1, 'tool_calls': 1,
                'messages': [], 'file_history': entries,
            }))
            payload = client.get('/api/file-history?limit=3').json()
            self.assertEqual(payload['total'], 10)
            self.assertEqual(payload['returned'], 3)
            self.assertEqual(len(payload['entries']), 3)


if __name__ == '__main__':
    unittest.main()
