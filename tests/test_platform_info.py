"""Tests for ``src/platform_info.py`` — platform detection and system dirs."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import platform_info
from src.platform_info import (
    SUPPORTED_PLATFORMS,
    LinuxDistroInfo,
    SystemDirectories,
    detect_vcs,
    get_linux_distro_info,
    get_platform,
    get_system_directories,
    get_wsl_version,
)


class GetPlatformTest(unittest.TestCase):
    def setUp(self) -> None:
        platform_info._reset_cache()

    def tearDown(self) -> None:
        platform_info._reset_cache()

    def test_macos(self) -> None:
        with mock.patch('src.platform_info.sys.platform', 'darwin'):
            self.assertEqual(get_platform(), 'macos')

    def test_windows(self) -> None:
        with mock.patch('src.platform_info.sys.platform', 'win32'):
            self.assertEqual(get_platform(), 'windows')

    def test_linux_no_wsl(self) -> None:
        with mock.patch('src.platform_info.sys.platform', 'linux'), \
                mock.patch(
                    'src.platform_info._read_proc_version',
                    return_value='Linux version 5.10 (gcc)',
                ):
            self.assertEqual(get_platform(), 'linux')

    def test_linux_wsl_microsoft_marker(self) -> None:
        with mock.patch('src.platform_info.sys.platform', 'linux'), \
                mock.patch(
                    'src.platform_info._read_proc_version',
                    return_value='Linux version 5.10 microsoft-standard-WSL2',
                ):
            self.assertEqual(get_platform(), 'wsl')

    def test_linux_proc_version_unreadable(self) -> None:
        with mock.patch('src.platform_info.sys.platform', 'linux'), \
                mock.patch(
                    'src.platform_info._read_proc_version',
                    side_effect=FileNotFoundError(),
                ):
            self.assertEqual(get_platform(), 'linux')

    def test_unknown_platform(self) -> None:
        with mock.patch('src.platform_info.sys.platform', 'sunos5'):
            self.assertEqual(get_platform(), 'unknown')

    def test_memoized(self) -> None:
        with mock.patch('src.platform_info.sys.platform', 'darwin'):
            self.assertEqual(get_platform(), 'macos')
        # Second call should hit cache, not re-evaluate sys.platform
        with mock.patch('src.platform_info.sys.platform', 'win32'):
            self.assertEqual(get_platform(), 'macos')

    def test_supported_platforms_contains_expected(self) -> None:
        self.assertIn('macos', SUPPORTED_PLATFORMS)
        self.assertIn('wsl', SUPPORTED_PLATFORMS)


class GetWslVersionTest(unittest.TestCase):
    def setUp(self) -> None:
        platform_info._reset_cache()

    def tearDown(self) -> None:
        platform_info._reset_cache()

    def test_explicit_wsl2(self) -> None:
        with mock.patch('src.platform_info.sys.platform', 'linux'), \
                mock.patch(
                    'src.platform_info._read_proc_version',
                    return_value='5.15.123-microsoft-standard-WSL2',
                ):
            self.assertEqual(get_wsl_version(), '2')

    def test_wsl1_fallback(self) -> None:
        with mock.patch('src.platform_info.sys.platform', 'linux'), \
                mock.patch(
                    'src.platform_info._read_proc_version',
                    return_value='4.4.0-19041-Microsoft (Microsoft@Microsoft.com)',
                ):
            self.assertEqual(get_wsl_version(), '1')

    def test_non_linux(self) -> None:
        with mock.patch('src.platform_info.sys.platform', 'darwin'):
            self.assertIsNone(get_wsl_version())

    def test_linux_no_microsoft_marker(self) -> None:
        with mock.patch('src.platform_info.sys.platform', 'linux'), \
                mock.patch(
                    'src.platform_info._read_proc_version',
                    return_value='Linux version 6.5.0 (gcc)',
                ):
            self.assertIsNone(get_wsl_version())


class GetLinuxDistroInfoTest(unittest.TestCase):
    def test_non_linux_returns_none(self) -> None:
        with mock.patch('src.platform_info.sys.platform', 'darwin'):
            self.assertIsNone(get_linux_distro_info())

    def test_parses_id_and_version(self) -> None:
        os_release = 'NAME="Ubuntu"\nID=ubuntu\nVERSION_ID="22.04"\n'
        with mock.patch('src.platform_info.sys.platform', 'linux'), \
                mock.patch(
                    'src.platform_info.Path.read_text', return_value=os_release,
                ):
            info = get_linux_distro_info()
        assert info is not None
        self.assertEqual(info.linux_distro_id, 'ubuntu')
        self.assertEqual(info.linux_distro_version, '22.04')
        self.assertIsNotNone(info.linux_kernel)

    def test_to_dict_skips_none(self) -> None:
        info = LinuxDistroInfo(linux_distro_id='fedora')
        self.assertEqual(info.to_dict(), {'linuxDistroId': 'fedora'})


class DetectVcsTest(unittest.TestCase):
    def test_detects_git(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '.git').mkdir()
            self.assertEqual(detect_vcs(tmp), ['git'])

    def test_detects_multiple(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '.git').mkdir()
            (Path(tmp) / '.hg').mkdir()
            self.assertEqual(detect_vcs(tmp), ['git', 'mercurial'])

    def test_perforce_via_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {'P4PORT': '1666'}):
            self.assertIn('perforce', detect_vcs(tmp))

    def test_unreadable_directory_returns_empty(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(detect_vcs('/nonexistent/path/abc/xyz'), [])


class GetSystemDirectoriesTest(unittest.TestCase):
    def test_macos_defaults(self) -> None:
        dirs = get_system_directories(
            home_dir='/Users/x', platform='macos', env={},
        )
        self.assertEqual(dirs.HOME, '/Users/x')
        self.assertEqual(dirs.DESKTOP, '/Users/x/Desktop')
        self.assertEqual(dirs.DOCUMENTS, '/Users/x/Documents')
        self.assertEqual(dirs.DOWNLOADS, '/Users/x/Downloads')

    def test_windows_uses_userprofile(self) -> None:
        dirs = get_system_directories(
            home_dir='C:/Users/old',
            platform='windows',
            env={'USERPROFILE': 'C:/Users/new'},
        )
        # Path normalizes to forward slashes on linux test runs; just check
        # USERPROFILE was used as the base, not home_dir.
        self.assertIn('Users/new', dirs.DESKTOP.replace('\\', '/'))
        self.assertIn('Users/new', dirs.DOWNLOADS.replace('\\', '/'))
        # HOME stays as the explicit home_dir
        self.assertEqual(dirs.HOME, 'C:/Users/old')

    def test_linux_xdg_overrides(self) -> None:
        dirs = get_system_directories(
            home_dir='/home/u',
            platform='linux',
            env={'XDG_DOWNLOAD_DIR': '/data/dl'},
        )
        self.assertEqual(dirs.DOWNLOADS, '/data/dl')
        self.assertEqual(dirs.DESKTOP, '/home/u/Desktop')

    def test_wsl_xdg_overrides(self) -> None:
        dirs = get_system_directories(
            home_dir='/home/u',
            platform='wsl',
            env={'XDG_DESKTOP_DIR': '/mnt/c/Users/x/Desktop'},
        )
        self.assertEqual(dirs.DESKTOP, '/mnt/c/Users/x/Desktop')

    def test_to_dict_round_trip(self) -> None:
        dirs = SystemDirectories(
            HOME='/h', DESKTOP='/h/D', DOCUMENTS='/h/Doc', DOWNLOADS='/h/Dn',
        )
        self.assertEqual(
            dirs.to_dict(),
            {'HOME': '/h', 'DESKTOP': '/h/D', 'DOCUMENTS': '/h/Doc', 'DOWNLOADS': '/h/Dn'},
        )


if __name__ == '__main__':
    unittest.main()
