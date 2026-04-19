"""Tests for ``src/git_utils.py``."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from src import git_utils
from src.git_utils import (
    find_git_root,
    get_repo_remote_hash,
    normalize_git_remote_url,
    should_include_git_instructions,
)


class FindGitRootTest(unittest.TestCase):
    def setUp(self) -> None:
        find_git_root.cache_clear()

    def test_finds_git_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '.git').mkdir()
            self.assertEqual(find_git_root(tmp), str(Path(tmp).resolve()))

    def test_walks_up_from_subdirectory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '.git').mkdir()
            sub = Path(tmp) / 'a' / 'b' / 'c'
            sub.mkdir(parents=True)
            self.assertEqual(find_git_root(str(sub)), str(Path(tmp).resolve()))

    def test_finds_when_git_is_a_file(self) -> None:
        # Worktrees and submodules use a .git file containing 'gitdir: ...'
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '.git').write_text('gitdir: /elsewhere/.git/worktrees/x')
            self.assertEqual(find_git_root(tmp), str(Path(tmp).resolve()))

    def test_returns_none_when_not_in_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(find_git_root(tmp))

    def test_memoizes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '.git').mkdir()
            first = find_git_root(tmp)
            # Now remove .git — second lookup should still hit cache
            (Path(tmp) / '.git').rmdir()
            self.assertEqual(find_git_root(tmp), first)


class NormalizeGitRemoteUrlTest(unittest.TestCase):
    def test_ssh_url(self) -> None:
        self.assertEqual(
            normalize_git_remote_url('git@github.com:org/repo.git'),
            'github.com/org/repo',
        )

    def test_ssh_url_no_dot_git_suffix(self) -> None:
        self.assertEqual(
            normalize_git_remote_url('git@github.com:org/repo'),
            'github.com/org/repo',
        )

    def test_https_url(self) -> None:
        self.assertEqual(
            normalize_git_remote_url('https://github.com/org/repo.git'),
            'github.com/org/repo',
        )

    def test_https_with_user(self) -> None:
        self.assertEqual(
            normalize_git_remote_url('https://user@github.com/org/repo.git'),
            'github.com/org/repo',
        )

    def test_ssh_protocol_url(self) -> None:
        self.assertEqual(
            normalize_git_remote_url('ssh://git@github.com/org/repo.git'),
            'github.com/org/repo',
        )

    def test_lowercases_result(self) -> None:
        self.assertEqual(
            normalize_git_remote_url('git@GitHub.com:Org/Repo.git'),
            'github.com/org/repo',
        )

    def test_ccr_proxy_legacy_assumes_github(self) -> None:
        self.assertEqual(
            normalize_git_remote_url('http://x@127.0.0.1:8080/git/org/repo'),
            'github.com/org/repo',
        )

    def test_ccr_proxy_ghe_uses_first_segment_as_host(self) -> None:
        self.assertEqual(
            normalize_git_remote_url(
                'http://x@127.0.0.1:8080/git/ghe.example.com/org/repo',
            ),
            'ghe.example.com/org/repo',
        )

    def test_returns_none_on_garbage(self) -> None:
        self.assertIsNone(normalize_git_remote_url(''))
        self.assertIsNone(normalize_git_remote_url('   '))
        self.assertIsNone(normalize_git_remote_url('not-a-url'))

    def test_localhost_alias(self) -> None:
        self.assertEqual(
            normalize_git_remote_url('http://localhost:8080/git/org/repo'),
            'github.com/org/repo',
        )


class GetRepoRemoteHashTest(unittest.TestCase):
    def test_hashes_normalized_url(self) -> None:
        url = 'git@github.com:Org/Repo.git'
        normalized = 'github.com/org/repo'
        expected = hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]
        self.assertEqual(get_repo_remote_hash(url), expected)

    def test_returns_none_for_empty(self) -> None:
        self.assertIsNone(get_repo_remote_hash(None))
        self.assertIsNone(get_repo_remote_hash(''))

    def test_returns_none_for_unparseable(self) -> None:
        self.assertIsNone(get_repo_remote_hash('not-a-url'))


class ShouldIncludeGitInstructionsTest(unittest.TestCase):
    def test_default_true_when_nothing_set(self) -> None:
        self.assertTrue(should_include_git_instructions(env={}))

    def test_env_truthy_disables(self) -> None:
        for value in ('1', 'true', 'yes', 'on'):
            self.assertFalse(
                should_include_git_instructions(
                    settings_value=True,
                    env={'CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS': value},
                ),
            )

    def test_env_falsy_overrides_settings(self) -> None:
        # Settings says off, but env explicitly says don't disable → on
        self.assertTrue(
            should_include_git_instructions(
                settings_value=False,
                env={'CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS': '0'},
            ),
        )

    def test_settings_value_used_when_env_unset(self) -> None:
        self.assertFalse(
            should_include_git_instructions(settings_value=False, env={}),
        )
        self.assertTrue(
            should_include_git_instructions(settings_value=True, env={}),
        )


if __name__ == '__main__':
    unittest.main()
