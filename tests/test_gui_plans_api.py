"""Integration tests for the GUI's `/api/plan` surface."""

from __future__ import annotations

import json
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


class PlansApiTests(unittest.TestCase):
    def test_get_returns_empty_plan(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            payload = client.get('/api/plan').json()
            self.assertEqual(payload['steps'], [])
            self.assertIsNone(payload['explanation'])

    def test_replace_persists_and_syncs_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            payload = client.put(
                '/api/plan',
                json={
                    'explanation': 'Land the GUI parity slices.',
                    'steps': [
                        {'step': 'Wire tasks view'},
                        {'step': 'Wire plans view', 'priority': 'high'},
                    ],
                    'sync_tasks': True,
                },
            ).json()
            self.assertEqual(len(payload['steps']), 2)
            self.assertEqual(payload['explanation'], 'Land the GUI parity slices.')

            store = Path(d) / '.port_sessions' / 'plan_runtime.json'
            self.assertTrue(store.exists())
            stored = json.loads(store.read_text())
            self.assertEqual(stored['steps'][1]['step'], 'Wire plans view')

            # sync_tasks=True replaces the local task list to mirror the plan.
            tasks = client.get('/api/tasks').json()['tasks']
            self.assertEqual(len(tasks), 2)

    def test_replace_rejects_invalid_status(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            r = client.put(
                '/api/plan',
                json={'steps': [{'step': 'X', 'status': 'nope'}]},
            )
            self.assertEqual(r.status_code, 400)

    def test_clear_empties_plan(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            client.put(
                '/api/plan',
                json={'steps': [{'step': 'X'}], 'sync_tasks': False},
            )
            after = client.post('/api/plan/clear', json={'sync_tasks': False}).json()
            self.assertEqual(after['steps'], [])


if __name__ == '__main__':
    unittest.main()
