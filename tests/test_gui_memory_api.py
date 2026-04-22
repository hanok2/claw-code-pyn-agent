"""Integration tests for the GUI's `/api/memory/*` surface."""

from __future__ import annotations

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


class MemoryApiTests(unittest.TestCase):
    def test_list_finds_local_claude_md(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cwd = Path(d)
            (cwd / 'CLAUDE.md').write_text('# rules\nbe terse\n', encoding='utf-8')
            client, _ = _client(cwd)
            payload = client.get('/api/memory').json()
            paths = [entry['path'] for entry in payload['files']]
            self.assertIn(str((cwd / 'CLAUDE.md').resolve()), paths)
            local_entry = next(
                e for e in payload['files'] if e['path'] == str((cwd / 'CLAUDE.md').resolve())
            )
            self.assertTrue(local_entry['writable'])

    def test_read_round_trips_content(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cwd = Path(d)
            target = cwd / 'CLAUDE.md'
            target.write_text('hello memory\n', encoding='utf-8')
            client, _ = _client(cwd)
            r = client.get('/api/memory/file', params={'path': str(target)})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()['content'], 'hello memory\n')

    def test_write_creates_and_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cwd = Path(d)
            target = cwd / '.claude' / 'rules' / 'style.md'
            client, _ = _client(cwd)
            r = client.put(
                '/api/memory/file',
                json={'path': str(target), 'content': 'rule one\n'},
            )
            self.assertEqual(r.status_code, 200)
            self.assertTrue(target.is_file())
            self.assertEqual(target.read_text(), 'rule one\n')

    def test_write_outside_roots_is_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
            client, _ = _client(Path(d))
            r = client.put(
                '/api/memory/file',
                json={'path': str(Path(outside) / 'CLAUDE.md'), 'content': 'no'},
            )
            self.assertEqual(r.status_code, 403)

    def test_delete_removes_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cwd = Path(d)
            target = cwd / 'CLAUDE.local.md'
            target.write_text('temporary', encoding='utf-8')
            client, _ = _client(cwd)
            r = client.delete('/api/memory/file', params={'path': str(target)})
            self.assertEqual(r.status_code, 200)
            self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
