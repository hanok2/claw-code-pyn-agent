"""Integration tests for the GUI's `/api/worktree` surface.

Spins a real git repo per test and exercises enter/exit through the API,
then verifies the agent's cwd was updated to follow the worktree.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.gui.server import AgentState, create_app


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True)


def _bootstrap_repo(root: Path) -> None:
    _git('init', '--initial-branch=main', '.', cwd=root)
    _git('config', 'user.email', 'test@example.com', cwd=root)
    _git('config', 'user.name', 'Test', cwd=root)
    (root / 'README.md').write_text('hello\n', encoding='utf-8')
    _git('add', '.', cwd=root)
    _git('commit', '-m', 'initial', cwd=root)


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


class WorktreeApiTests(unittest.TestCase):
    def test_status_outside_repo_reports_inactive(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _client(Path(d))
            payload = client.get('/api/worktree').json()
            self.assertFalse(payload['status']['active'])
            self.assertEqual(payload['history'], [])

    def test_enter_swaps_cwd_and_records_history(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / 'repo'
            repo.mkdir()
            _bootstrap_repo(repo)
            client, state = _client(repo)

            r = client.post('/api/worktree/enter', json={'name': 'feat1'})
            self.assertEqual(r.status_code, 200)
            payload = r.json()
            self.assertTrue(payload['status']['active'])
            self.assertIn('feat1', payload['status']['session_name'])
            # State.cwd should have moved into the new worktree.
            self.assertEqual(str(state.cwd), payload['status']['current_cwd'])
            self.assertNotEqual(str(state.cwd), str(repo.resolve()))

            history = payload['history']
            self.assertEqual(history[-1]['action'], 'enter')

    def test_exit_restores_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / 'repo'
            repo.mkdir()
            _bootstrap_repo(repo)
            client, state = _client(repo)

            client.post('/api/worktree/enter', json={'name': 'feat2'})
            r = client.post('/api/worktree/exit', json={'action': 'remove'})
            self.assertEqual(r.status_code, 200)
            payload = r.json()
            self.assertFalse(payload['status']['active'])
            # Back in the repo root.
            self.assertEqual(state.cwd, repo.resolve())

    def test_enter_outside_repo_returns_400(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _client(Path(d))
            r = client.post('/api/worktree/enter', json={'name': 'x'})
            self.assertEqual(r.status_code, 400)


if __name__ == '__main__':
    unittest.main()
