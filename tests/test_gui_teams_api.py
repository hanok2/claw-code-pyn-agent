"""Integration tests for the GUI's `/api/teams` surface."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.gui.server import AgentState, create_app


def _client(tmp: Path) -> TestClient:
    state = AgentState(
        cwd=tmp,
        model='test-model',
        base_url='http://127.0.0.1:8000/v1',
        api_key='local-token',
        allow_shell=False,
        allow_write=False,
        session_directory=tmp / 'sessions',
    )
    return TestClient(create_app(state))


class TeamsApiTests(unittest.TestCase):
    def test_starts_empty(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            payload = client.get('/api/teams').json()
            self.assertEqual(payload['teams'], [])
            self.assertEqual(payload['messages'], [])

    def test_create_team_then_send_message(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            client.post('/api/teams', json={'name': 'core', 'members': ['alice', 'bob']})

            r = client.post(
                '/api/teams/core/messages',
                json={'text': 'hello', 'sender': 'alice'},
            )
            self.assertEqual(r.status_code, 200)
            payload = r.json()
            self.assertEqual(payload['message']['text'], 'hello')
            self.assertEqual(len(payload['state']['messages']), 1)

    def test_create_duplicate_team_returns_409(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            client.post('/api/teams', json={'name': 't'})
            r = client.post('/api/teams', json={'name': 't'})
            self.assertEqual(r.status_code, 409)

    def test_delete_team_drops_messages(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            client.post('/api/teams', json={'name': 'core'})
            client.post(
                '/api/teams/core/messages', json={'text': 'x', 'sender': 'a'}
            )
            payload = client.delete('/api/teams/core').json()
            self.assertEqual(payload['teams'], [])
            self.assertEqual(payload['messages'], [])

    def test_send_to_unknown_team_returns_404(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            r = client.post(
                '/api/teams/missing/messages', json={'text': 'x', 'sender': 'a'}
            )
            self.assertEqual(r.status_code, 404)


if __name__ == '__main__':
    unittest.main()
