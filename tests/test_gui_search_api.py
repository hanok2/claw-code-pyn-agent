"""Integration tests for the GUI's `/api/search` surface.

The actual `query` endpoint hits real network providers, so we don't
exercise it here.  Discovery + activation + 404s are all that the GUI
guarantees today; live queries are a runtime concern.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.gui.server import AgentState, create_app


def _write_manifest(cwd: Path) -> None:
    (cwd / '.claw-search.json').write_text(json.dumps({
        'providers': [
            {
                'name': 'searx',
                'provider': 'searxng',
                'base_url': 'http://127.0.0.1:8080',
                'description': 'local searxng',
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


class SearchApiTests(unittest.TestCase):
    def test_status_with_no_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            payload = client.get('/api/search').json()
            self.assertEqual(payload['providers'], [])
            self.assertIsNone(payload['active_provider_name'])

    def test_list_finds_manifest_provider(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cwd = Path(d)
            _write_manifest(cwd)
            client = _client(cwd)
            payload = client.get('/api/search').json()
            names = [p['name'] for p in payload['providers']]
            self.assertIn('searx', names)

    def test_activate_persists_active_provider(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cwd = Path(d)
            _write_manifest(cwd)
            client = _client(cwd)
            r = client.post('/api/search/activate/searx')
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()['active_provider_name'], 'searx')

    def test_activate_unknown_returns_404(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            r = client.post('/api/search/activate/missing')
            self.assertEqual(r.status_code, 404)


if __name__ == '__main__':
    unittest.main()
