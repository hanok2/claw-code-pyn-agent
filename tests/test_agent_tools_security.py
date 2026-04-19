"""Security tests for agent_tools.py: path traversal, destructive commands, and env var filtering."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.agent_tools import (
    ToolExecutionError,
    ToolPermissionError,
    _build_subprocess_env,
    _ensure_shell_allowed,
    _is_sensitive_env_var,
    _resolve_path,
    build_tool_context,
    default_tool_registry,
)
from src.agent_types import AgentPermissions, AgentRuntimeConfig
from src.session_env_vars import (
    clear_session_env_vars,
    set_session_env_var,
)


def _make_context(
    tmp_dir: str,
    *,
    allow_shell: bool = False,
    allow_destructive: bool = False,
) -> "ToolExecutionContext":  # noqa: F821
    config = AgentRuntimeConfig(
        cwd=Path(tmp_dir),
        permissions=AgentPermissions(
            allow_shell_commands=allow_shell,
            allow_destructive_shell_commands=allow_destructive,
        ),
    )
    return build_tool_context(config, tool_registry=default_tool_registry())


# ---------------------------------------------------------------------------
# _resolve_path – path traversal prevention
# ---------------------------------------------------------------------------
class TestResolvePath(unittest.TestCase):
    def test_relative_path_within_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "hello.txt").write_text("hi")
            ctx = _make_context(tmp)
            result = _resolve_path("hello.txt", ctx)
            self.assertEqual(result, (Path(tmp) / "hello.txt").resolve())

    def test_absolute_path_within_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sub" / "file.txt"
            target.parent.mkdir()
            target.write_text("data")
            ctx = _make_context(tmp)
            result = _resolve_path(str(target), ctx)
            self.assertEqual(result, target.resolve())

    def test_traversal_with_dotdot_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _make_context(tmp)
            with self.assertRaises(ToolExecutionError):
                _resolve_path("../outside", ctx)

    def test_traversal_etc_passwd_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _make_context(tmp)
            with self.assertRaises(ToolExecutionError):
                _resolve_path("../../etc/passwd", ctx)

    def test_allow_missing_true_permits_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _make_context(tmp)
            result = _resolve_path("does_not_exist.txt", ctx, allow_missing=True)
            self.assertEqual(result, (Path(tmp) / "does_not_exist.txt").resolve())

    def test_allow_missing_false_raises_for_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _make_context(tmp)
            with self.assertRaises(OSError):
                _resolve_path("does_not_exist.txt", ctx, allow_missing=False)


# ---------------------------------------------------------------------------
# _ensure_shell_allowed – destructive command blocking
# ---------------------------------------------------------------------------
class TestEnsureShellAllowed(unittest.TestCase):
    def _ctx(self, *, allow_shell: bool = True, allow_destructive: bool = False) -> "ToolExecutionContext":  # noqa: F821
        self._tmp = tempfile.TemporaryDirectory()
        return _make_context(
            self._tmp.name,
            allow_shell=allow_shell,
            allow_destructive=allow_destructive,
        )

    def tearDown(self):
        if hasattr(self, "_tmp"):
            self._tmp.cleanup()

    # -- safe commands pass --------------------------------------------------
    def test_safe_commands_allowed(self):
        ctx = self._ctx()
        for cmd in ("ls -la", "cat file.txt", "echo hello", "grep foo bar.txt"):
            _ensure_shell_allowed(cmd, ctx)  # should not raise

    # -- destructive commands blocked -----------------------------------------
    def test_rm_blocked(self):
        ctx = self._ctx()
        with self.assertRaises(ToolPermissionError):
            _ensure_shell_allowed("rm -rf /", ctx)

    def test_mv_blocked(self):
        ctx = self._ctx()
        with self.assertRaises(ToolPermissionError):
            _ensure_shell_allowed("mv a b", ctx)

    def test_dd_blocked(self):
        ctx = self._ctx()
        with self.assertRaises(ToolPermissionError):
            _ensure_shell_allowed("dd if=/dev/zero of=/dev/sda", ctx)

    def test_shutdown_blocked(self):
        ctx = self._ctx()
        with self.assertRaises(ToolPermissionError):
            _ensure_shell_allowed("shutdown -h now", ctx)

    def test_reboot_blocked(self):
        ctx = self._ctx()
        with self.assertRaises(ToolPermissionError):
            _ensure_shell_allowed("reboot ", ctx)

    def test_mkfs_blocked(self):
        ctx = self._ctx()
        with self.assertRaises(ToolPermissionError):
            _ensure_shell_allowed("mkfs.ext4 /dev/sda1", ctx)

    def test_chmod_recursive_777_blocked(self):
        ctx = self._ctx()
        with self.assertRaises(ToolPermissionError):
            _ensure_shell_allowed("chmod -R 777 /", ctx)

    def test_chown_recursive_blocked(self):
        ctx = self._ctx()
        with self.assertRaises(ToolPermissionError):
            _ensure_shell_allowed("chown -R root:root /", ctx)

    def test_git_reset_hard_blocked(self):
        ctx = self._ctx()
        with self.assertRaises(ToolPermissionError):
            _ensure_shell_allowed("git reset --hard", ctx)

    def test_git_clean_fd_blocked(self):
        ctx = self._ctx()
        with self.assertRaises(ToolPermissionError):
            _ensure_shell_allowed("git clean -fd", ctx)

    def test_truncation_operator_blocked(self):
        ctx = self._ctx()
        with self.assertRaises(ToolPermissionError):
            _ensure_shell_allowed(": > important.log", ctx)

    # -- chained commands with destructive sub-commands -----------------------
    def test_chained_and_blocked(self):
        ctx = self._ctx()
        with self.assertRaises(ToolPermissionError):
            _ensure_shell_allowed("echo hi && rm -rf /", ctx)

    def test_chained_or_blocked(self):
        ctx = self._ctx()
        with self.assertRaises(ToolPermissionError):
            _ensure_shell_allowed("false || rm file", ctx)

    def test_chained_semicolon_blocked(self):
        ctx = self._ctx()
        with self.assertRaises(ToolPermissionError):
            _ensure_shell_allowed("echo ok; mv a b", ctx)

    # -- shell commands entirely disabled ------------------------------------
    def test_shell_disabled_raises(self):
        ctx = self._ctx(allow_shell=False)
        with self.assertRaises(ToolPermissionError):
            _ensure_shell_allowed("ls", ctx)

    # -- allow_destructive bypasses blocking ---------------------------------
    def test_destructive_allowed_bypasses(self):
        ctx = self._ctx(allow_destructive=True)
        # All destructive commands should pass without raising
        for cmd in (
            "rm -rf /",
            "mv a b",
            "dd if=/dev/zero of=/dev/sda",
            "shutdown -h now",
            "mkfs.ext4 /dev/sda1",
            "chmod -R 777 /",
            "chown -R root:root /",
            "git reset --hard",
            "git clean -fd",
            ": > file",
        ):
            _ensure_shell_allowed(cmd, ctx)  # should not raise


# ---------------------------------------------------------------------------
# _is_sensitive_env_var – secret-name detection
# ---------------------------------------------------------------------------
class TestIsSensitiveEnvVar(unittest.TestCase):
    def test_common_sensitive_vars_detected(self):
        for name in (
            "MY_SECRET",
            "GITHUB_TOKEN",
            "DB_PASSWORD",
            "SSH_PRIVATE_KEY",
            "MY_API_KEY",
            "CREDENTIAL_STORE",
            "AUTH_HEADER",
        ):
            self.assertTrue(
                _is_sensitive_env_var(name),
                f"{name} should be detected as sensitive",
            )

    def test_non_sensitive_vars_allowed(self):
        for name in ("HOME", "PATH", "LANG", "TERM", "USER", "SHELL"):
            self.assertFalse(
                _is_sensitive_env_var(name),
                f"{name} should not be detected as sensitive",
            )

    def test_case_insensitive(self):
        self.assertTrue(_is_sensitive_env_var("my_secret"))
        self.assertTrue(_is_sensitive_env_var("Github_Token"))
        self.assertTrue(_is_sensitive_env_var("db_password"))


# ---------------------------------------------------------------------------
# _build_subprocess_env – session env var merging
# ---------------------------------------------------------------------------
class TestBuildSubprocessEnv(unittest.TestCase):
    def setUp(self):
        clear_session_env_vars()

    def tearDown(self):
        clear_session_env_vars()

    def test_session_env_var_appears_in_subprocess_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _make_context(tmp)
            set_session_env_var("CLAW_SESSION_FOO", "from-session")
            env = _build_subprocess_env(ctx)
            self.assertEqual(env["CLAW_SESSION_FOO"], "from-session")

    def test_extra_env_overrides_session_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = AgentRuntimeConfig(cwd=Path(tmp))
            ctx = build_tool_context(
                config,
                tool_registry=default_tool_registry(),
                extra_env={"CLAW_OVERRIDE_ME": "from-extra"},
            )
            set_session_env_var("CLAW_OVERRIDE_ME", "from-session")
            env = _build_subprocess_env(ctx)
            self.assertEqual(env["CLAW_OVERRIDE_ME"], "from-extra")


if __name__ == "__main__":
    unittest.main()
