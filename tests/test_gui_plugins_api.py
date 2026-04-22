"""Integration tests for the GUI's `/api/plugins` surface."""

from __future__ import annotations

import json
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
    return TestClient(create_app(state))


class PluginsApiTests(unittest.TestCase):
    def test_list_with_no_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            payload = client.get('/api/plugins').json()
            self.assertEqual(payload['manifests'], [])

    def test_list_finds_local_plugin_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cwd = Path(d)
            plugin_dir = cwd / '.claw-plugin'
            plugin_dir.mkdir()
            (plugin_dir / 'plugin.json').write_text(json.dumps({
                'name': 'demo',
                'description': 'a demo plugin',
                'tools': ['demo_tool'],
                'hooks': {'before_prompt': 'remember to demo'},
            }), encoding='utf-8')
            client = _client(cwd)
            payload = client.get('/api/plugins').json()
            names = [m['name'] for m in payload['manifests']]
            self.assertIn('demo', names)
            demo = next(m for m in payload['manifests'] if m['name'] == 'demo')
            self.assertEqual(demo['tool_names'], ['demo_tool'])
            self.assertEqual(demo['before_prompt'], 'remember to demo')


if __name__ == '__main__':
    unittest.main()
