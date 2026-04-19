"""Tests for discovery slash commands ported from the npm source.

Covers /version, /init, /ide, /plugin, /remote-env.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.agent_runtime import LocalCodingAgent
from src.agent_slash_commands import preprocess_slash_command
from src.agent_types import AgentRuntimeConfig, ModelConfig


def _make_agent(tmp_dir: str) -> LocalCodingAgent:
    return LocalCodingAgent(
        model_config=ModelConfig(model='test-model'),
        runtime_config=AgentRuntimeConfig(cwd=Path(tmp_dir)),
    )


def _local_settings(tmp_dir: str) -> dict:
    path = Path(tmp_dir) / '.claude' / 'settings.local.json'
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


class VersionCommandTest(unittest.TestCase):
    def test_prints_python_runtime_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/version').final_output
        self.assertIn('claw-code-agent', out)
        self.assertIn('Python', out)


class InitCommandTest(unittest.TestCase):
    def test_returns_prompt_with_claude_md_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            result = preprocess_slash_command(agent, '/init')
        self.assertTrue(result.handled)
        self.assertTrue(result.should_query)
        self.assertIn('CLAUDE.md', result.prompt or '')
        self.assertIn('analyze this codebase', (result.prompt or '').lower())


class IdeCommandTest(unittest.TestCase):
    def test_no_ide_when_env_clean(self) -> None:
        clean = {k: v for k, v in os.environ.items() if k not in {
            'TERM_PROGRAM', 'VSCODE_INJECTION', 'VSCODE_PID',
            'JETBRAINS_IDE', 'TERMINAL_EMULATOR', 'SSH_CONNECTION',
        }}
        with mock.patch.dict(os.environ, clean, clear=True):
            with tempfile.TemporaryDirectory() as tmp:
                agent = _make_agent(tmp)
                out = agent.run('/ide').final_output
        self.assertIn('No IDE detected', out)
        self.assertIn('IDE auto-connect', out)

    def test_detects_vscode(self) -> None:
        env = {'VSCODE_PID': '1234', 'TERM_PROGRAM': 'vscode'}
        with mock.patch.dict(os.environ, env, clear=True):
            with tempfile.TemporaryDirectory() as tmp:
                agent = _make_agent(tmp)
                out = agent.run('/ide').final_output
        self.assertIn('Visual Studio Code', out)
        self.assertIn('VSCODE_PID=1234', out)


class PluginCommandTest(unittest.TestCase):
    def test_lists_no_plugins_when_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/plugin').final_output
        self.assertIn('No installed plugins', out)

    def test_help_describes_usage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/plugin help').final_output
        self.assertIn('Usage: /plugin', out)
        self.assertIn('list', out)

    def test_unknown_subcommand(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/plugin bogus').final_output
        self.assertIn('Unknown plugin subcommand', out)


class RemoteEnvCommandTest(unittest.TestCase):
    def test_lists_empty_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/remote-env').final_output
        self.assertIn('Available remote environments', out)
        self.assertIn('no profiles found', out)
        self.assertIn('Usage:', out)

    def test_clear_when_no_default_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/remote-env clear').final_output
        self.assertIn('No default remote environment', out)

    def test_unknown_profile_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/remote-env nope').final_output
        self.assertIn('Unknown remote environment', out)
        self.assertIn('nope', out)

    def test_set_then_clear_persists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '.remote.json').write_text(json.dumps({
                'profiles': [
                    {'name': 'sandbox', 'mode': 'ssh', 'target': 'user@host'},
                ],
            }), encoding='utf-8')
            agent = _make_agent(tmp)
            set_out = agent.run('/remote-env sandbox').final_output
            self.assertIn('Default remote environment set to sandbox', set_out)
            self.assertEqual(_local_settings(tmp).get('defaultRemoteEnvironment'), 'sandbox')

            agent2 = _make_agent(tmp)
            list_out = agent2.run('/remote-env').final_output
            self.assertIn('sandbox', list_out)
            self.assertIn('(default)', list_out)

            clear_out = agent2.run('/remote-env clear').final_output
            self.assertIn('Cleared default remote environment', clear_out)
            self.assertIsNone(_local_settings(tmp).get('defaultRemoteEnvironment'))


if __name__ == '__main__':
    unittest.main()
