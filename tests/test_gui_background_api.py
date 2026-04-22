"""Integration tests for the GUI's `/api/background/*` surface."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.gui.server import AgentState, create_app


def _client(tmp: Path) -> tuple[TestClient, AgentState]:
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


def _write_record(root: Path, *, background_id: str, status: str = 'exited', pid: int = 0) -> None:
    """Drop a synthetic background record + log into the runtime root."""
    root.mkdir(parents=True, exist_ok=True)
    record = {
        'background_id': background_id,
        'pid': pid,
        'prompt': 'demo prompt',
        'workspace_cwd': str(root.parent.parent),
        'model': 'test-model',
        'mode': 'agent',
        'status': status,
        'log_path': str(root / f'{background_id}.log'),
        'record_path': str(root / f'{background_id}.json'),
        'started_at': '2026-04-22T00:00:00+00:00',
        'command': ['python', '-m', 'src.main', 'agent-bg-worker', background_id, 'demo'],
        'exit_code': 0 if status == 'completed' else None,
    }
    (root / f'{background_id}.json').write_text(json.dumps(record), encoding='utf-8')
    (root / f'{background_id}.log').write_text(f'log for {background_id}\n', encoding='utf-8')


class BackgroundApiTests(unittest.TestCase):
    def test_list_starts_empty(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _client(Path(d))
            payload = client.get('/api/background').json()
            self.assertEqual(payload['sessions'], [])
            self.assertEqual(payload['counts']['running'], 0)

    def test_list_surfaces_persisted_records(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cwd = Path(d)
            root = cwd / '.port_sessions' / 'background'
            _write_record(root, background_id='bg_alpha', status='exited')
            _write_record(root, background_id='bg_beta', status='completed')
            client, _ = _client(cwd)
            payload = client.get('/api/background').json()
            ids = {sess['background_id'] for sess in payload['sessions']}
            self.assertEqual(ids, {'bg_alpha', 'bg_beta'})
            self.assertEqual(payload['counts']['completed'], 1)

    def test_logs_returns_content(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cwd = Path(d)
            root = cwd / '.port_sessions' / 'background'
            _write_record(root, background_id='bg_logs', status='completed')
            client, _ = _client(cwd)
            r = client.get('/api/background/bg_logs/logs').json()
            self.assertIn('log for bg_logs', r['content'])

    def test_get_unknown_returns_404(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _client(Path(d))
            r = client.get('/api/background/bg_nope')
            self.assertEqual(r.status_code, 404)
            r = client.get('/api/background/bg_nope/logs')
            self.assertEqual(r.status_code, 404)
            r = client.post('/api/background/bg_nope/kill')
            self.assertEqual(r.status_code, 404)

    def test_kill_on_already_finished_session_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cwd = Path(d)
            root = cwd / '.port_sessions' / 'background'
            _write_record(root, background_id='bg_done', status='completed')
            client, _ = _client(cwd)
            r = client.post('/api/background/bg_done/kill')
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()['status'], 'completed')


if __name__ == '__main__':
    unittest.main()
