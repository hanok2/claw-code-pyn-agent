"""Tests for settings-touching slash commands ported from the npm source.

Covers /theme, /voice, /sandbox-toggle (alias /sandbox), /keybindings, /btw.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.agent_runtime import LocalCodingAgent
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


class ThemeCommandTest(unittest.TestCase):
    def test_lists_themes_when_no_arg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/theme').final_output
        self.assertIn('Available themes', out)
        self.assertIn('light', out)
        self.assertIn('dark', out)
        self.assertIn('Usage: /theme <name>', out)

    def test_rejects_unknown_theme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/theme neon').final_output
        self.assertIn('Unknown theme', out)
        self.assertIn('neon', out)

    def test_sets_theme_and_persists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/theme dark').final_output
            self.assertIn('Theme set to dark', out)
            settings = _local_settings(tmp)
        self.assertEqual(settings.get('theme'), 'dark')

    def test_marks_current_theme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            agent.run('/theme dark')
            out = agent.run('/theme').final_output
        self.assertIn('dark (current)', out)


class VoiceCommandTest(unittest.TestCase):
    def test_toggle_enables_when_unset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/voice').final_output
            self.assertIn('Voice mode enabled', out)
            self.assertEqual(_local_settings(tmp).get('voiceEnabled'), True)

    def test_toggle_disables_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            agent.run('/voice on')
            out = agent.run('/voice').final_output
            self.assertIn('Voice mode disabled', out)
            self.assertEqual(_local_settings(tmp).get('voiceEnabled'), False)

    def test_explicit_on_off(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            self.assertIn('enabled', agent.run('/voice on').final_output)
            self.assertIn('disabled', agent.run('/voice off').final_output)

    def test_rejects_unknown_arg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/voice maybe').final_output
        self.assertIn('Usage', out)


class SandboxToggleCommandTest(unittest.TestCase):
    def test_status_with_no_args(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/sandbox-toggle').final_output
        self.assertIn('Sandbox:', out)
        self.assertIn('Excluded commands', out)
        self.assertIn('Usage:', out)

    def test_alias_sandbox(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/sandbox').final_output
        self.assertIn('Sandbox:', out)

    def test_exclude_appends_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/sandbox-toggle exclude "npm run test:*"').final_output
            self.assertIn('Added "npm run test:*"', out)
            settings = _local_settings(tmp)
        excluded = settings.get('sandbox', {}).get('excludedCommands', [])
        self.assertIn('npm run test:*', excluded)

    def test_exclude_dedupes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            agent.run('/sandbox-toggle exclude "rm -rf /"')
            out = agent.run('/sandbox-toggle exclude "rm -rf /"').final_output
        self.assertIn('already in', out)

    def test_exclude_requires_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/sandbox-toggle exclude').final_output
        self.assertIn('Usage', out)

    def test_unknown_subcommand(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/sandbox-toggle wat').final_output
        self.assertIn('Unknown subcommand', out)


class KeybindingsCommandTest(unittest.TestCase):
    def test_creates_template_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            out = agent.run('/keybindings').final_output
            path = Path(tmp) / '.claude' / 'keybindings.json'
            self.assertTrue(path.exists())
            self.assertIn('Created', out)
            self.assertIn(str(path), out)
            # Template is valid JSON-ish (has braces); strict json.loads would
            # choke on the "//" comment, so just sanity-check structure.
            text = path.read_text(encoding='utf-8')
            self.assertIn('"bindings"', text)

    def test_reports_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            agent.run('/keybindings')
            out = agent.run('/keybindings').final_output
        self.assertIn('Found', out)


class BtwCommandTest(unittest.TestCase):
    def test_no_question_shows_usage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            result = agent.run('/btw').final_output
        self.assertIn('Usage: /btw', result)

    def test_question_returns_prompt_result(self) -> None:
        from src.agent_slash_commands import preprocess_slash_command

        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            result = preprocess_slash_command(agent, '/btw what does this codebase do?')
        self.assertTrue(result.handled)
        self.assertTrue(result.should_query)
        self.assertIn('side question', (result.prompt or '').lower())
        self.assertIn('what does this codebase do?', result.prompt or '')


if __name__ == '__main__':
    unittest.main()
