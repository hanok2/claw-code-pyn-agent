"""Tests for remote/bridge slash commands ported from the npm source.

Covers /bridge (aliases /remote-control, /rc) and /remote-setup
(alias /web-setup).
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.agent_runtime import LocalCodingAgent
from src.agent_types import AgentRuntimeConfig, ModelConfig


def _make_agent(tmp_dir: str) -> LocalCodingAgent:
    return LocalCodingAgent(
        model_config=ModelConfig(model='test-model'),
        runtime_config=AgentRuntimeConfig(cwd=Path(tmp_dir)),
    )


class BridgeCommandTest(unittest.TestCase):
    def test_reports_unsupported_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/bridge').final_output
        self.assertIn('not implemented', out.lower())
        self.assertIn('No active local remote connection', out)

    def test_remote_control_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/remote-control').final_output
        self.assertIn('Remote-control bridge', out)

    def test_rc_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/rc').final_output
        self.assertIn('Remote-control bridge', out)

    def test_named_lookup_misses_unknown_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/bridge nope').final_output
        self.assertIn('No matching remote profile for "nope"', out)

    def test_named_lookup_matches_known_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '.remote.json').write_text(json.dumps({
                'profiles': [
                    {'name': 'edge', 'mode': 'ssh', 'target': 'user@edge.example'},
                ],
            }), encoding='utf-8')
            agent = _make_agent(tmp)
            out = agent.run('/bridge edge').final_output
        self.assertIn('Matched remote profile "edge"', out)
        self.assertIn('user@edge.example', out)


class RemoteSetupCommandTest(unittest.TestCase):
    def test_includes_web_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/remote-setup').final_output
        self.assertIn('https://claude.ai/code', out)
        self.assertIn('GitHub CLI', out)

    def test_web_setup_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/web-setup').final_output
        self.assertIn('https://claude.ai/code', out)

    def test_handles_missing_gh(self) -> None:
        with mock.patch('shutil.which', return_value=None):
            with tempfile.TemporaryDirectory() as tmp:
                agent = _make_agent(tmp)
                out = agent.run('/remote-setup').final_output
        self.assertIn('not_installed', out)
        self.assertIn('cli.github.com', out)

    def test_handles_authenticated_gh(self) -> None:
        fake = mock.Mock(returncode=0, stdout='Logged in to github.com as octo', stderr='')
        with mock.patch('shutil.which', return_value='/usr/bin/gh'), \
             mock.patch('subprocess.run', return_value=fake):
            with tempfile.TemporaryDirectory() as tmp:
                agent = _make_agent(tmp)
                out = agent.run('/remote-setup').final_output
        self.assertIn('authenticated', out)
        self.assertIn('gh auth token', out)

    def test_handles_unauthenticated_gh(self) -> None:
        fake = mock.Mock(returncode=1, stdout='', stderr='You are not logged into any GitHub hosts')
        with mock.patch('shutil.which', return_value='/usr/bin/gh'), \
             mock.patch('subprocess.run', return_value=fake):
            with tempfile.TemporaryDirectory() as tmp:
                agent = _make_agent(tmp)
                out = agent.run('/remote-setup').final_output
        self.assertIn('not_authenticated', out)
        self.assertIn('gh auth login', out)


if __name__ == '__main__':
    unittest.main()
