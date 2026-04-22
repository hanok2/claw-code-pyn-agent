"""Integration tests for the GUI's `/api/tasks/*` surface.

The tasks router reads a fresh :class:`TaskRuntime` per request from the
GUI's current cwd, so the tests just point an :class:`AgentState` at a temp
dir and exercise the round trip.
"""

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


class TasksApiTests(unittest.TestCase):
    def test_list_starts_empty(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            payload = client.get('/api/tasks').json()
            self.assertEqual(payload['tasks'], [])
            self.assertEqual(payload['counts']['pending'], 0)

    def test_create_then_list_and_persist(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            r = client.post('/api/tasks', json={'title': 'Wire the GUI'})
            self.assertEqual(r.status_code, 200)
            payload = r.json()
            self.assertEqual(payload['task']['title'], 'Wire the GUI')

            tasks = client.get('/api/tasks').json()['tasks']
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0]['status'], 'pending')

            store = Path(d) / '.port_sessions' / 'task_runtime.json'
            self.assertTrue(store.exists())
            stored = json.loads(store.read_text())
            self.assertEqual(stored['tasks'][0]['title'], 'Wire the GUI')

    def test_complete_unblocks_dependents(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            a = client.post('/api/tasks', json={'title': 'A'}).json()['task']
            b = client.post(
                '/api/tasks',
                json={'title': 'B', 'blocked_by': [a['task_id']], 'status': 'blocked'},
            ).json()['task']
            self.assertEqual(b['status'], 'blocked')

            done = client.post(f'/api/tasks/{a["task_id"]}/complete').json()
            tasks_by_id = {t['task_id']: t for t in done['state']['tasks']}
            self.assertEqual(tasks_by_id[a['task_id']]['status'], 'completed')
            # Completing A should re-open B since its only dependency is gone.
            self.assertEqual(tasks_by_id[b['task_id']]['status'], 'pending')

    def test_update_rejects_unknown_status(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            t = client.post('/api/tasks', json={'title': 'X'}).json()['task']
            r = client.patch(
                f'/api/tasks/{t["task_id"]}', json={'status': 'not-a-status'}
            )
            self.assertEqual(r.status_code, 400)

    def test_cancel_records_reason(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            t = client.post('/api/tasks', json={'title': 'Y'}).json()['task']
            r = client.post(
                f'/api/tasks/{t["task_id"]}/cancel', json={'reason': 'no longer needed'}
            )
            self.assertEqual(r.status_code, 200)
            cancelled = r.json()['task']
            self.assertEqual(cancelled['status'], 'cancelled')
            self.assertEqual(cancelled['metadata'].get('cancel_reason'), 'no longer needed')

    def test_actions_404_on_unknown_task(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            for path in (
                '/api/tasks/missing',
                '/api/tasks/missing/start',
                '/api/tasks/missing/complete',
            ):
                method = client.patch if path == '/api/tasks/missing' else client.post
                r = method(path, json={})
                self.assertEqual(r.status_code, 404, path)


if __name__ == '__main__':
    unittest.main()
