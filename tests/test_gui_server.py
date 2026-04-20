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


if __name__ == '__main__':
    unittest.main()
