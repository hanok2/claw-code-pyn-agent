"""Tests for the informational slash commands ported from the npm source.

Covers /output-style, /release-notes, /feedback, /upgrade, /stickers, /mobile,
/desktop, /install-github-app, /install-slack-app, /privacy-settings,
/extra-usage, /passes, /rate-limit-options, /chrome, /reload-plugins.
"""

from __future__ import annotations

import os
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


class ExternalSlashCommandsTest(unittest.TestCase):
    """Each test runs with CLAUDE_CODE_NO_BROWSER=1 so no browser opens."""

    def setUp(self) -> None:
        os.environ['CLAUDE_CODE_NO_BROWSER'] = '1'

    def tearDown(self) -> None:
        os.environ.pop('CLAUDE_CODE_NO_BROWSER', None)

    def _run(self, cmd: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent(tmp)
            return agent.run(cmd).final_output

    def test_output_style_is_deprecated(self) -> None:
        out = self._run('/output-style')
        self.assertIn('deprecated', out.lower())
        self.assertIn('/config', out)

    def test_release_notes_falls_back_to_link(self) -> None:
        out = self._run('/release-notes')
        self.assertIn('CHANGELOG.md', out)
        self.assertIn('https://github.com/anthropics/claude-code', out)

    def test_release_notes_reads_local_changelog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'CHANGELOG.md').write_text(
                '# Changelog\n\n## 1.2.3\n- did a thing\n\n## 1.2.2\n- old\n',
                encoding='utf-8',
            )
            agent = _make_agent(tmp)
            out = agent.run('/release-notes').final_output
        self.assertIn('1.2.3', out)
        self.assertIn('did a thing', out)
        self.assertNotIn('1.2.2', out)

    def test_feedback_returns_link(self) -> None:
        out = self._run('/feedback')
        self.assertIn('https://github.com/anthropics/claude-code/issues', out)

    def test_bug_aliases_to_feedback(self) -> None:
        out = self._run('/bug')
        self.assertIn('https://github.com/anthropics/claude-code/issues', out)

    def test_feedback_includes_user_note(self) -> None:
        out = self._run('/feedback the wrap selector keeps eating my prompt')
        self.assertIn('Draft note', out)
        self.assertIn('wrap selector', out)

    def test_upgrade_returns_link(self) -> None:
        out = self._run('/upgrade')
        self.assertIn('https://claude.ai/upgrade/max', out)

    def test_stickers_returns_link(self) -> None:
        out = self._run('/stickers')
        self.assertIn('stickermule.com/claudecode', out)

    def test_mobile_lists_both_stores(self) -> None:
        out = self._run('/mobile')
        self.assertIn('apps.apple.com', out)
        self.assertIn('play.google.com', out)

    def test_ios_alias(self) -> None:
        out = self._run('/ios')
        self.assertIn('apps.apple.com', out)

    def test_android_alias(self) -> None:
        out = self._run('/android')
        self.assertIn('play.google.com', out)

    def test_desktop_returns_link(self) -> None:
        out = self._run('/desktop')
        self.assertIn('claude.ai/download', out)

    def test_app_aliases_to_desktop(self) -> None:
        out = self._run('/app')
        self.assertIn('claude.ai/download', out)

    def test_install_github_app(self) -> None:
        out = self._run('/install-github-app')
        self.assertIn('github.com/apps/claude', out)

    def test_install_slack_app(self) -> None:
        out = self._run('/install-slack-app')
        self.assertIn('slack.com/marketplace/A08SF47R6P4-claude', out)

    def test_privacy_settings(self) -> None:
        out = self._run('/privacy-settings')
        self.assertIn('claude.ai/settings/data-privacy-controls', out)

    def test_extra_usage_points_to_upgrade(self) -> None:
        out = self._run('/extra-usage')
        self.assertIn('claude.ai/upgrade/max', out)
        self.assertIn('/login', out)

    def test_passes_mentions_claude_ai(self) -> None:
        out = self._run('/passes')
        self.assertIn('claude.ai', out.lower())
        self.assertIn('passes', out.lower())

    def test_rate_limit_options_lists_actions(self) -> None:
        out = self._run('/rate-limit-options')
        self.assertIn('/upgrade', out)
        self.assertIn('/extra-usage', out)
        self.assertIn('/login', out)

    def test_chrome_returns_link(self) -> None:
        out = self._run('/chrome')
        self.assertIn('claude.ai/chrome', out)

    def test_reload_plugins_reports_counts(self) -> None:
        out = self._run('/reload-plugins')
        self.assertIn('Reloaded plugins', out)
        self.assertIn('plugin(s)', out)
        self.assertIn('tool(s)', out)
        self.assertIn('hook(s)', out)


if __name__ == '__main__':
    unittest.main()
