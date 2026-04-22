"""Integration tests for the GUI's `/api/remote-triggers` surface."""

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


class RemoteTriggersApiTests(unittest.TestCase):
    def test_starts_empty(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            payload = client.get('/api/remote-triggers').json()
            self.assertEqual(payload['triggers'], [])
            self.assertEqual(payload['history'], [])

    def test_create_then_run_records_history(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            create = client.post(
                '/api/remote-triggers',
                json={'trigger_id': 'deploy', 'workflow': 'deploy_prod'},
            )
            self.assertEqual(create.status_code, 200)
            self.assertEqual(create.json()['triggers'][0]['workflow'], 'deploy_prod')

            run = client.post(
                '/api/remote-triggers/deploy/run',
                json={'body': {'env': 'prod'}},
            )
            self.assertEqual(run.status_code, 200)
            payload = run.json()
            self.assertEqual(payload['record']['trigger_id'], 'deploy')
            self.assertEqual(payload['record']['body'], {'env': 'prod'})
            self.assertEqual(len(payload['state']['history']), 1)

    def test_create_duplicate_returns_409(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            client.post('/api/remote-triggers', json={'trigger_id': 't'})
            r = client.post('/api/remote-triggers', json={'trigger_id': 't'})
            self.assertEqual(r.status_code, 409)

    def test_update_unknown_returns_404(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            r = client.patch('/api/remote-triggers/missing', json={'name': 'x'})
            self.assertEqual(r.status_code, 404)


if __name__ == '__main__':
    unittest.main()
