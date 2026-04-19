"""Tests for setup-time runtime checks ported from setup.ts."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.setup import (
    MIN_PYTHON_VERSION,
    SetupReport,
    check_runtime_requirements,
    run_setup,
)


class RuntimeRequirementCheckTest(unittest.TestCase):
    def test_python_check_passes_on_current_runtime(self) -> None:
        checks = {check.name: check for check in check_runtime_requirements()}
        self.assertTrue(checks['python_version'].ok)
        self.assertGreaterEqual(sys.version_info[:2], MIN_PYTHON_VERSION)

    def test_python_check_fails_when_below_minimum(self) -> None:
        # Force a lower version_info via patching to verify the failure branch.
        fake_version = mock.Mock()
        fake_version.__getitem__ = lambda self, idx: (3, 8)[idx] if isinstance(idx, int) else (3, 8)[idx]
        with mock.patch('src.setup.sys') as fake_sys:
            fake_sys.version_info = (3, 8, 0)
            checks = {check.name: check for check in check_runtime_requirements()}
        self.assertFalse(checks['python_version'].ok)
        self.assertIn('below required', checks['python_version'].detail)

    def test_includes_platform_and_implementation(self) -> None:
        names = {check.name for check in check_runtime_requirements()}
        self.assertIn('python_implementation', names)
        self.assertIn('platform', names)


class SetupReportTest(unittest.TestCase):
    def test_run_setup_reports_runtime_and_release_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'CHANGELOG.md').write_text(
                '# Changelog\n\n## 9.9.9\n- big release\n', encoding='utf-8',
            )
            report = run_setup(cwd=Path(tmp), trusted=True, last_seen_version='0.0.1')
        self.assertIsInstance(report, SetupReport)
        self.assertGreaterEqual(len(report.runtime_checks), 3)
        self.assertIn('big release', report.release_notes)
        markdown = report.as_markdown()
        self.assertIn('Runtime checks', markdown)
        self.assertIn('Release notes', markdown)
        self.assertFalse(report.has_blocking_issues())

    def test_no_release_notes_when_changelog_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_setup(cwd=Path(tmp), trusted=True)
        self.assertEqual(report.release_notes, ())
        self.assertNotIn('Release notes', report.as_markdown())


if __name__ == '__main__':
    unittest.main()
