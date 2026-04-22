"""Integration tests for the GUI's `/api/account` surface.

The account runtime discovers profile manifests on disk, persists login
state under `.port_sessions/account_runtime.json`, and emits a status
report.  Tests drop a manifest into the temp workspace and exercise the
full login → status → logout cycle through the API.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.gui.server import AgentState, create_app


def _write_manifest(cwd: Path) -> None:
    manifest = cwd / '.claude' / 'account.json'
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({
        'profiles': [
            {
                'name': 'local-vllm',
                'provider': 'openai',
                'identity': 'local-token',
                'description': 'local vLLM server',
                'auth_mode': 'token',
                'api_base': 'http://127.0.0.1:8000/v1',
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


class AccountApiTests(unittest.TestCase):
    def test_status_with_no_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _client(Path(d))
            payload = client.get('/api/account').json()
            self.assertFalse(payload['status']['logged_in'])
            self.assertEqual(payload['profiles'], [])

    def test_login_named_profile_persists(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cwd = Path(d)
            _write_manifest(cwd)
            client, _ = _client(cwd)

            r = client.post('/api/account/login', json={'target': 'local-vllm'})
            self.assertEqual(r.status_code, 200)
            payload = r.json()
            self.assertTrue(payload['status']['logged_in'])
            self.assertEqual(payload['status']['profile_name'], 'local-vllm')
            self.assertTrue((cwd / '.port_sessions' / 'account_runtime.json').exists())

    def test_login_ephemeral_when_profile_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _client(Path(d))
            r = client.post(
                '/api/account/login',
                json={'target': 'sk-token', 'provider': 'openrouter', 'auth_mode': 'bearer'},
            )
            payload = r.json()
            self.assertTrue(payload['status']['logged_in'])
            self.assertEqual(payload['status']['identity'], 'sk-token')
            self.assertEqual(payload['status']['provider'], 'openrouter')

    def test_logout_clears_active_session(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _client(Path(d))
            client.post('/api/account/login', json={'target': 'tmp-id'})
            r = client.post('/api/account/logout', json={'reason': 'test'})
            self.assertFalse(r.json()['status']['logged_in'])


if __name__ == '__main__':
    unittest.main()
