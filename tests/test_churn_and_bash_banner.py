"""Markdown-churn guard + bash self-authored banner.

Two more reasoning-pattern guards:

1. Churn-doc: model writes successive summary/findings/critical-finding
   markdown files as fake progress markers. Each is a different path so
   the per-path edit-loop limit doesn't catch it. Cumulative count does.

2. Bash banner: when the agent runs a script it wrote earlier in the
   session (e.g., `python3 my_test.py`), the captured output is prefixed
   with a [self-authored: ...] banner. Mirrors the read-time warning
   for execution-time results.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.agent_tools import (
    ToolExecutionError,
    _is_churn_markdown,
    _run_bash,
    _write_file,
    build_tool_context,
    default_tool_registry,
)
from src.agent_types import AgentPermissions, AgentRuntimeConfig


def _ctx(tmp: str, *, allow_shell: bool = False):
    return build_tool_context(
        AgentRuntimeConfig(
            cwd=Path(tmp),
            permissions=AgentPermissions(
                allow_file_write=True,
                allow_shell_commands=allow_shell,
                allow_destructive_shell_commands=False,
            ),
        ),
        tool_registry=default_tool_registry(),
    )


class TestChurnPattern(unittest.TestCase):
    def test_recognises_summary_finding_critical_session_filenames(self):
        for name in [
            'CRITICAL_FINDING_20260504.md',
            'SESSION_SUMMARY_20260504.md',
            'gaps_filled_20260504.md',
            'QUICK_REFERENCE.md',
            'FINAL_SUMMARY.md',
            'completion_report.md',
            'implementation_summary.md',
            'wrap-up.md',
        ]:
            assert _is_churn_markdown(Path('/tmp') / name), name

    def test_excludes_legitimate_doc_files(self):
        for name in ['README.md', 'CHANGELOG.md', 'LICENSE.md', 'CONTRIBUTING.md']:
            assert not _is_churn_markdown(Path('/tmp') / name), name

    def test_excludes_files_in_docs_directory(self):
        # Even if the filename matches "summary", being in docs/ makes it
        # legitimate documentation.
        assert not _is_churn_markdown(Path('/proj/docs/architecture_summary.md'))

    def test_non_md_files_not_churn(self):
        assert not _is_churn_markdown(Path('/tmp/SESSION_SUMMARY.txt'))


class TestChurnGuard(unittest.TestCase):
    def test_excessive_summary_writes_eventually_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _ctx(tmp)
            for i in range(4):
                _write_file({
                    'path': f'CRITICAL_FINDING_{i}.md',
                    'content': '# something\n',
                }, ctx)
            # The 5th churn-shaped write triggers the guard.
            with self.assertRaises(ToolExecutionError) as cm:
                _write_file({
                    'path': 'CRITICAL_FINDING_5.md',
                    'content': '# something\n',
                }, ctx)
            msg = str(cm.exception)
            self.assertIn('churn-doc guard', msg)
            self.assertIn('not progress', msg)

    def test_legitimate_doc_writes_do_not_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _ctx(tmp)
            for name in ['README.md', 'CHANGELOG.md', 'LICENSE.md', 'CONTRIBUTING.md']:
                _write_file({'path': name, 'content': '# x\n'}, ctx)
            # All four legitimate docs written. Now write a churn doc;
            # should still be the FIRST churn write, not the 5th.
            _write_file({'path': 'SESSION_SUMMARY.md', 'content': '# x\n'}, ctx)
            self.assertEqual(ctx.edit_history.get('__churn_md_count__'), 1)


class TestBashSelfAuthoredBanner(unittest.TestCase):
    def test_running_self_authored_script_gets_banner(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _ctx(tmp, allow_shell=True)
            _write_file({
                'path': 'my_test.py',
                'content': 'print("hi")\n',
            }, ctx)
            output = _run_bash({'command': 'python3 my_test.py'}, ctx)
            text = output[0] if isinstance(output, tuple) else output
            self.assertIn('[self-authored:', text)
            self.assertIn('my_test.py', text)
            self.assertIn('not an independent measurement', text)
            self.assertIn('hi', text)  # actual output preserved

    def test_running_external_command_no_banner(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _ctx(tmp, allow_shell=True)
            output = _run_bash({'command': 'echo hello'}, ctx)
            text = output[0] if isinstance(output, tuple) else output
            self.assertNotIn('[self-authored:', text)
            self.assertIn('hello', text)

    def test_unrelated_command_after_self_write_no_banner(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _ctx(tmp, allow_shell=True)
            _write_file({'path': 'measurement.py', 'content': 'x = 1\n'}, ctx)
            # Run a command that does NOT reference the self-authored file.
            output = _run_bash({'command': 'echo done'}, ctx)
            text = output[0] if isinstance(output, tuple) else output
            self.assertNotIn('[self-authored:', text)


if __name__ == '__main__':
    unittest.main()
