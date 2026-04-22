"""Integration tests for the GUI's `/api/mcp` surface.

Drops a synthetic `.claw-mcp.json` manifest into the workspace and walks
through discovery + read-resource against an inline resource (no real MCP
server needed).  Tool calls require a live stdio server, which we don't
have in CI, so they're not exercised here.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.gui.server import AgentState, create_app


def _write_manifest(cwd: Path) -> None:
    (cwd / '.claw-mcp.json').write_text(json.dumps({
        'name': 'docs',
        'resources': [
            {
                'uri': 'docs://hello',
                'name': 'hello',
                'description': 'inline hello text',
                'text': 'hello world',
            }
        ],
        'servers': [
            {
                'name': 'docs',
                'command': '/bin/true',
                'description': 'no-op stdio server (just for discovery)',
            }
        ],
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


class McpApiTests(unittest.TestCase):
    def test_status_with_no_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _client(Path(d))
            payload = client.get('/api/mcp').json()
            self.assertEqual(payload['servers'], [])
            self.assertEqual(payload['resources'], [])

    def test_status_surfaces_manifest_resources_and_servers(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cwd = Path(d)
            _write_manifest(cwd)
            client, _ = _client(cwd)
            payload = client.get('/api/mcp').json()
            uris = {r['uri'] for r in payload['resources']}
            self.assertIn('docs://hello', uris)
            names = {s['name'] for s in payload['servers']}
            self.assertIn('docs', names)

    def test_read_inline_resource(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cwd = Path(d)
            _write_manifest(cwd)
            client, _ = _client(cwd)
            r = client.post('/api/mcp/resources/read', json={'uri': 'docs://hello'})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()['content'], 'hello world')

    def test_read_unknown_resource_returns_404(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client, _ = _client(Path(d))
            r = client.post('/api/mcp/resources/read', json={'uri': 'docs://nope'})
            self.assertEqual(r.status_code, 404)


if __name__ == '__main__':
    unittest.main()
