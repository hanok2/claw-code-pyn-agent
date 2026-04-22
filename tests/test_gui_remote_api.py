"""Integration tests for the GUI's `/api/remote` surface.

Mirrors the account-runtime tests: drop a manifest in the temp workspace,
verify discovery + connect + disconnect persist correctly.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.gui.server import AgentState, create_app


def _write_manifest(cwd: Path) -> None:
    manifest = cwd / '.claw-remote.json'
    manifest.write_text(json.dumps({
        'profiles': [
            {
                'name': 'box-a',
                'mode': 'ssh',
                'target': 'user@host:port',
                'description': 'shared dev box',
            }
        ]
    }), encoding='utf-8')


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


class RemoteApiTests(unittest.TestCase):
    def test_status_with_no_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _client(Path(d))
            payload = client.get('/api/remote').json()
            self.assertFalse(payload['status']['connected'])
            self.assertEqual(payload['profiles'], [])

    def test_connect_named_profile(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cwd = Path(d)
            _write_manifest(cwd)
            client, _ = _client(cwd)

            payload = client.post('/api/remote/connect', json={'target': 'box-a'}).json()
            self.assertTrue(payload['status']['connected'])
            self.assertEqual(payload['status']['profile_name'], 'box-a')
            self.assertTrue((cwd / '.port_sessions' / 'remote_runtime.json').exists())

    def test_connect_ephemeral_target(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _client(Path(d))
            payload = client.post(
                '/api/remote/connect',
                json={'target': '10.0.0.5', 'mode': 'ssh'},
            ).json()
            self.assertTrue(payload['status']['connected'])
            self.assertEqual(payload['status']['target'], '10.0.0.5')

    def test_disconnect_clears_state(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _client(Path(d))
            client.post('/api/remote/connect', json={'target': 'tmp'})
            payload = client.post('/api/remote/disconnect', json={'reason': 'test'}).json()
            self.assertFalse(payload['status']['connected'])


if __name__ == '__main__':
    unittest.main()
