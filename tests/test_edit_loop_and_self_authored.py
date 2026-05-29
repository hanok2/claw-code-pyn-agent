"""Edit-loop guard + self-authored artifact tagging.

Two reasoning-pattern guards extracted from the Latti S127 transcript:

1. Edit-loop: model edited the same test file 8-10 times tweaking
   thresholds back and forth. Pure churn. Guard refuses after N writes
   to the same path within one tool-context lifetime.

2. Self-authored: model wrote a "retrieval accuracy test" then ran it
   then cited the result as if it were an objective measurement. The
   tagging prepends a skepticism header to any read of a file the
   agent wrote earlier in the same session.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.agent_tools import (
    ToolExecutionError,
    _edit_file,
    _read_file,
    _write_file,
    build_tool_context,
    default_tool_registry,
)
from src.agent_types import AgentPermissions, AgentRuntimeConfig


def _ctx(tmp: str):
    return build_tool_context(
        AgentRuntimeConfig(
            cwd=Path(tmp),
            permissions=AgentPermissions(
                allow_file_write=True,
                allow_shell_commands=False,
                allow_destructive_shell_commands=False,
            ),
        ),
        tool_registry=default_tool_registry(),
    )


class TestEditLoopGuard(unittest.TestCase):
    def test_repeated_writes_to_same_file_eventually_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _ctx(tmp)
            for i in range(5):
                _write_file({'path': 'foo.py', 'content': f'# rev {i}\n'}, ctx)
            with self.assertRaises(ToolExecutionError) as cm:
                _write_file({'path': 'foo.py', 'content': '# rev 6\n'}, ctx)
            msg = str(cm.exception)
            self.assertIn('edit-loop guard', msg)
            self.assertIn('tweak-and-rerun', msg)

    def test_writes_to_different_files_do_not_count_against_each_other(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _ctx(tmp)
            for i in range(5):
                _write_file({'path': f'a_{i}.py', 'content': '# x\n'}, ctx)
            # 6th write to a NEW file should still succeed.
            _write_file({'path': 'a_6.py', 'content': '# x\n'}, ctx)
            self.assertEqual(ctx.edit_history.get(
                str((Path(tmp) / 'a_6.py').resolve())
            ), 1)

    def test_edit_after_loop_limit_also_refused(self):
        """Mixing _edit_file and _write_file on the same path counts together."""
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _ctx(tmp)
            _write_file({'path': 'foo.py', 'content': 'hello there\n'}, ctx)
            for _ in range(4):
                _edit_file(
                    {'path': 'foo.py', 'old_text': 'hello', 'new_text': 'hello'},
                    ctx,
                )
            # That's 1 write + 4 edits = 5. Sixth touch refused.
            with self.assertRaises(ToolExecutionError) as cm:
                _edit_file(
                    {'path': 'foo.py', 'old_text': 'hello', 'new_text': 'hi'},
                    ctx,
                )
            self.assertIn('edit-loop guard', str(cm.exception))


class TestSelfAuthoredTagging(unittest.TestCase):
    def test_read_after_self_write_includes_warning_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _ctx(tmp)
            _write_file(
                {'path': 'measurement.py', 'content': 'def m(): return 0.42\n'},
                ctx,
            )
            content = _read_file({'path': 'measurement.py'}, ctx)
            self.assertIn('[self-authored:', content)
            self.assertIn('not independent measurements', content)
            self.assertIn('return 0.42', content)

    def test_read_of_external_file_no_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            # File created externally (e.g., by user, or pre-existed)
            (Path(tmp) / 'external.md').write_text('user-written content\n')
            ctx = _ctx(tmp)
            content = _read_file({'path': 'external.md'}, ctx)
            self.assertNotIn('[self-authored:', content)
            self.assertIn('user-written content', content)

    def test_self_authored_warning_with_line_range(self):
        """Warning header must also appear when read uses start_line/end_line."""
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _ctx(tmp)
            _write_file(
                {'path': 'm.py', 'content': 'a\nb\nc\nd\ne\n'},
                ctx,
            )
            content = _read_file({'path': 'm.py', 'start_line': 2, 'end_line': 4}, ctx)
            self.assertIn('[self-authored:', content)


if __name__ == '__main__':
    unittest.main()
