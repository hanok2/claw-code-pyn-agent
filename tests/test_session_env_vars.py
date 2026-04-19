"""Tests for ``src/session_env_vars.py``."""

from __future__ import annotations

import unittest

from src.session_env_vars import (
    clear_session_env_vars,
    delete_session_env_var,
    get_session_env_vars,
    set_session_env_var,
)


class SessionEnvVarsTest(unittest.TestCase):
    def setUp(self) -> None:
        clear_session_env_vars()

    def tearDown(self) -> None:
        clear_session_env_vars()

    def test_starts_empty(self) -> None:
        self.assertEqual(dict(get_session_env_vars()), {})

    def test_set_and_get(self) -> None:
        set_session_env_var('FOO', 'bar')
        self.assertEqual(get_session_env_vars()['FOO'], 'bar')

    def test_set_overwrites_existing(self) -> None:
        set_session_env_var('FOO', 'one')
        set_session_env_var('FOO', 'two')
        self.assertEqual(get_session_env_vars()['FOO'], 'two')

    def test_delete_removes(self) -> None:
        set_session_env_var('FOO', 'bar')
        delete_session_env_var('FOO')
        self.assertNotIn('FOO', get_session_env_vars())

    def test_delete_missing_is_noop(self) -> None:
        delete_session_env_var('NEVER_SET')
        self.assertEqual(dict(get_session_env_vars()), {})

    def test_clear_drops_everything(self) -> None:
        set_session_env_var('A', '1')
        set_session_env_var('B', '2')
        clear_session_env_vars()
        self.assertEqual(dict(get_session_env_vars()), {})

    def test_returned_mapping_is_read_only(self) -> None:
        set_session_env_var('FOO', 'bar')
        view = get_session_env_vars()
        with self.assertRaises(TypeError):
            view['FOO'] = 'mutated'  # type: ignore[index]

    def test_view_reflects_subsequent_mutations(self) -> None:
        view = get_session_env_vars()
        self.assertNotIn('FOO', view)
        set_session_env_var('FOO', 'bar')
        self.assertEqual(view['FOO'], 'bar')


if __name__ == '__main__':
    unittest.main()
