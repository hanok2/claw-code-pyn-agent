"""Integration tests for the GUI's `/api/workflows` surface."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.gui.server import AgentState, create_app


def _write_manifest(cwd: Path) -> None:
    (cwd / '.claw-workflows.json').write_text(json.dumps({
        'workflows': [
            {
                'name': 'echo',
                'description': 'echo a value',
                'prompt': 'Echo {{value}}',
                'steps': [{'prompt': 'echo {{value}}'}],
            }
        ]
    }), encoding='utf-8')


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


class WorkflowApiTests(unittest.TestCase):
    def test_list_with_no_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            payload = client.get('/api/workflows').json()
            self.assertEqual(payload['workflows'], [])

    def test_list_finds_manifest_workflows(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cwd = Path(d)
            _write_manifest(cwd)
            client = _client(cwd)
            payload = client.get('/api/workflows').json()
            names = [w['name'] for w in payload['workflows']]
            self.assertIn('echo', names)

    def test_run_records_history(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cwd = Path(d)
            _write_manifest(cwd)
            client = _client(cwd)
            r = client.post('/api/workflows/echo/run', json={'arguments': {'value': 'ok'}})
            self.assertEqual(r.status_code, 200)
            payload = r.json()
            self.assertEqual(payload['record']['workflow_name'], 'echo')
            self.assertEqual(payload['record']['arguments'], {'value': 'ok'})
            self.assertEqual(len(payload['state']['history']), 1)

    def test_run_unknown_workflow_returns_404(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            r = client.post('/api/workflows/missing/run', json={})
            self.assertEqual(r.status_code, 404)


if __name__ == '__main__':
    unittest.main()
