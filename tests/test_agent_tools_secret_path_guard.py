"""Production-tool secret-bearing path guard.

The runtime tools in `agent_tools.py` (`_read_file`, `_edit_file`,
`_grep_search`) are the ones the model actually invokes via the tool
registry. This pins those production paths.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.agent_tools import (
    ToolExecutionError,
    _edit_file,
    _grep_search,
    _read_file,
    build_tool_context,
    default_tool_registry,
)
from src.agent_types import AgentPermissions, AgentRuntimeConfig


def _ctx(tmp: str, *, allow_write: bool = False):
    config = AgentRuntimeConfig(
        cwd=Path(tmp),
        permissions=AgentPermissions(
            allow_shell_commands=False,
            allow_destructive_shell_commands=False,
            allow_file_write=allow_write,
        ),
    )
    return build_tool_context(config, tool_registry=default_tool_registry())


class TestReadFileGuard(unittest.TestCase):
    def test_read_file_refuses_dotenv(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '.env').write_text('SECRET=abc\n')
            ctx = _ctx(tmp)
            with self.assertRaises(ToolExecutionError) as cm:
                _read_file({'path': '.env'}, ctx)
            self.assertIn('refused to read secret-bearing path', str(cm.exception))

    def test_read_file_refuses_pem(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'key.pem').write_text('-----BEGIN PRIVATE KEY-----\nx\n')
            ctx = _ctx(tmp)
            with self.assertRaises(ToolExecutionError):
                _read_file({'path': 'key.pem'}, ctx)

    def test_read_file_allows_normal_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'README.md').write_text('hi')
            ctx = _ctx(tmp)
            self.assertIn('hi', _read_file({'path': 'README.md'}, ctx))


class TestEditFileGuard(unittest.TestCase):
    def test_edit_file_refuses_dotenv(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '.env').write_text('SECRET=abc')
            ctx = _ctx(tmp, allow_write=True)
            with self.assertRaises(ToolExecutionError) as cm:
                _edit_file(
                    {'path': '.env', 'old_text': 'abc', 'new_text': 'def'},
                    ctx,
                )
            self.assertIn('refused to read secret-bearing path', str(cm.exception))


class TestSymlinkResolution(unittest.TestCase):
    """If a non-secret-named symlink points at a secret-bearing target,
    the guard must catch it. The check resolves to the real path before
    matching against the pattern set.
    """

    def test_symlink_to_dotenv_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp) / '.env'
            real.write_text('SECRET=abc\n')
            link = Path(tmp) / 'config.txt'
            link.symlink_to(real)
            ctx = _ctx(tmp)
            # The guard's pattern set matches names ending in .env. After
            # `_resolve_path` resolves the symlink, the target's name is .env
            # and the guard fires.
            with self.assertRaises(ToolExecutionError) as cm:
                _read_file({'path': 'config.txt'}, ctx)
            self.assertIn('refused to read secret-bearing path', str(cm.exception))


class TestGrepSearchGuard(unittest.TestCase):
    def test_grep_explicit_dotenv_path_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '.env').write_text('SECRET=abc123\n')
            ctx = _ctx(tmp)
            with self.assertRaises(ToolExecutionError):
                _grep_search({'pattern': 'SECRET', 'path': '.env'}, ctx)

    def test_grep_directory_silently_skips_dotenv(self):
        """Greping a directory should not leak .env contents but should not
        fail loudly — silent skip preserves the user's directory-grep intent.
        """
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '.env').write_text('SECRET=hunter2\n')
            (Path(tmp) / 'README.md').write_text('SECRET feature here\n')
            ctx = _ctx(tmp)
            out = _grep_search({'pattern': 'SECRET', 'path': '.'}, ctx)
            assert 'hunter2' not in out
            assert 'feature here' in out


if __name__ == '__main__':
    unittest.main()
