"""Integration tests for the GUI's `/api/diagnostics` surface."""

from __future__ import annotations

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


class DiagnosticsApiTests(unittest.TestCase):
    def test_index_lists_known_reports(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            payload = client.get('/api/diagnostics').json()
            names = {r['name'] for r in payload['reports']}
            for expected in (
                'summary',
                'manifest',
                'parity-audit',
                'setup-report',
                'command-graph',
                'tool-pool',
                'bootstrap-graph',
            ):
                self.assertIn(expected, names)

    def test_summary_returns_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            r = client.get('/api/diagnostics/summary')
            self.assertEqual(r.status_code, 200)
            payload = r.json()
            self.assertEqual(payload['name'], 'summary')
            self.assertTrue(payload['content'])

    def test_unknown_report_returns_404(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            r = client.get('/api/diagnostics/nope')
            self.assertEqual(r.status_code, 404)


if __name__ == '__main__':
    unittest.main()
