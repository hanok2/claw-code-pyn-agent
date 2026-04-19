"""Tests for ``src/ide_path_conversion.py``."""

from __future__ import annotations

import subprocess
import unittest
from unittest import mock

from src.ide_path_conversion import (
    WindowsToWSLConverter,
    check_wsl_distro_match,
)


class CheckWslDistroMatchTest(unittest.TestCase):
    def test_matches_named_distro(self) -> None:
        self.assertTrue(
            check_wsl_distro_match(r'\\wsl$\Ubuntu\home\me', 'Ubuntu'),
        )

    def test_matches_localhost_form(self) -> None:
        self.assertTrue(
            check_wsl_distro_match(
                r'\\wsl.localhost\Ubuntu\home\me', 'Ubuntu',
            ),
        )

    def test_mismatch(self) -> None:
        self.assertFalse(
            check_wsl_distro_match(r'\\wsl$\Debian\home\me', 'Ubuntu'),
        )

    def test_non_unc_path_returns_true(self) -> None:
        self.assertTrue(check_wsl_distro_match(r'C:\Users\me', 'Ubuntu'))


class WindowsToWSLConverterToLocalPathTest(unittest.TestCase):
    def test_empty_path_passthrough(self) -> None:
        conv = WindowsToWSLConverter('Ubuntu')
        self.assertEqual(conv.to_local_path(''), '')

    def test_uses_wslpath_when_available(self) -> None:
        conv = WindowsToWSLConverter(None)
        with mock.patch(
            'src.ide_path_conversion.subprocess.run',
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout='/mnt/c/Users/me\n', stderr='',
            ),
        ) as run:
            self.assertEqual(conv.to_local_path(r'C:\Users\me'), '/mnt/c/Users/me')
            run.assert_called_once()
            args = run.call_args[0][0]
            self.assertEqual(args, ['wslpath', '-u', r'C:\Users\me'])

    def test_falls_back_to_manual_when_wslpath_missing(self) -> None:
        conv = WindowsToWSLConverter(None)
        with mock.patch(
            'src.ide_path_conversion.subprocess.run',
            side_effect=FileNotFoundError(),
        ):
            self.assertEqual(
                conv.to_local_path(r'C:\Users\me'), '/mnt/c/Users/me',
            )

    def test_falls_back_to_manual_on_called_process_error(self) -> None:
        conv = WindowsToWSLConverter(None)
        with mock.patch(
            'src.ide_path_conversion.subprocess.run',
            side_effect=subprocess.CalledProcessError(1, 'wslpath'),
        ):
            self.assertEqual(
                conv.to_local_path(r'D:\path\to\file.txt'),
                '/mnt/d/path/to/file.txt',
            )

    def test_different_distro_path_returned_as_is(self) -> None:
        conv = WindowsToWSLConverter('Ubuntu')
        with mock.patch(
            'src.ide_path_conversion.subprocess.run',
        ) as run:
            self.assertEqual(
                conv.to_local_path(r'\\wsl$\Debian\home\me'),
                r'\\wsl$\Debian\home\me',
            )
            run.assert_not_called()

    def test_same_distro_unc_uses_wslpath(self) -> None:
        conv = WindowsToWSLConverter('Ubuntu')
        with mock.patch(
            'src.ide_path_conversion.subprocess.run',
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout='/home/me\n', stderr='',
            ),
        ) as run:
            self.assertEqual(
                conv.to_local_path(r'\\wsl$\Ubuntu\home\me'),
                '/home/me',
            )
            run.assert_called_once()


class WindowsToWSLConverterToIdePathTest(unittest.TestCase):
    def test_empty_passthrough(self) -> None:
        conv = WindowsToWSLConverter(None)
        self.assertEqual(conv.to_ide_path(''), '')

    def test_uses_wslpath(self) -> None:
        conv = WindowsToWSLConverter(None)
        with mock.patch(
            'src.ide_path_conversion.subprocess.run',
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout=r'\\wsl$\Ubuntu\home\me' + '\n',
                stderr='',
            ),
        ) as run:
            self.assertEqual(
                conv.to_ide_path('/home/me'), r'\\wsl$\Ubuntu\home\me',
            )
            run.assert_called_once()
            args = run.call_args[0][0]
            self.assertEqual(args, ['wslpath', '-w', '/home/me'])

    def test_returns_original_on_failure(self) -> None:
        conv = WindowsToWSLConverter(None)
        with mock.patch(
            'src.ide_path_conversion.subprocess.run',
            side_effect=FileNotFoundError(),
        ):
            self.assertEqual(conv.to_ide_path('/home/me'), '/home/me')


if __name__ == '__main__':
    unittest.main()
