"""Integration tests for the GUI's `/api/ask-user` surface."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.ask_user_runtime import AskUserRuntime
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


class AskUserApiTests(unittest.TestCase):
    def test_status_starts_empty(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            payload = client.get('/api/ask-user').json()
            self.assertEqual(payload['queued_answers'], [])
            self.assertEqual(payload['history'], [])

    def test_enqueue_then_runtime_consumes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cwd = Path(d)
            client = _client(cwd)
            r = client.post(
                '/api/ask-user/queue',
                json={
                    'question': 'Are you sure?',
                    'answer': 'yes',
                    'match': 'exact',
                },
            )
            self.assertEqual(r.status_code, 200)
            self.assertEqual(len(r.json()['queued_answers']), 1)

            # The agent's own runtime — same cwd — should be able to consume it.
            runtime = AskUserRuntime.from_workspace(cwd)
            response = runtime.answer(question='Are you sure?')
            self.assertEqual(response.answer, 'yes')

    def test_remove_queued_by_index(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            client.post('/api/ask-user/queue', json={'answer': 'a', 'question': 'q1'})
            client.post('/api/ask-user/queue', json={'answer': 'b', 'question': 'q2'})
            payload = client.delete('/api/ask-user/queue/0').json()
            answers = [a['answer'] for a in payload['queued_answers']]
            self.assertEqual(answers, ['b'])

    def test_remove_unknown_index_returns_404(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            client = _client(Path(d))
            r = client.delete('/api/ask-user/queue/5')
            self.assertEqual(r.status_code, 404)

    def test_clear_history_empties_log(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cwd = Path(d)
            client = _client(cwd)
            client.post('/api/ask-user/queue', json={'answer': 'a', 'question': 'q'})
            # Consume to record one history entry.
            AskUserRuntime.from_workspace(cwd).answer(question='q')
            after = client.post('/api/ask-user/clear-history').json()
            self.assertEqual(after['history'], [])


if __name__ == '__main__':
    unittest.main()
