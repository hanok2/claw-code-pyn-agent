"""Tests for the local release-notes parser ported from utils/releaseNotes.ts."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.release_notes import (
    MAX_RELEASE_NOTES_SHOWN,
    check_for_release_notes,
    get_all_release_notes,
    get_recent_release_notes,
    parse_changelog,
    read_local_changelog,
)


SAMPLE = (
    '# Changelog\n\n'
    '## 1.3.0 - 2026-04-15\n'
    '- new shiny\n'
    '- another bullet\n\n'
    '## 1.2.0\n'
    '- mid bullet\n\n'
    '## 1.1.0\n'
    '- oldest bullet\n'
)


class ParseChangelogTest(unittest.TestCase):
    def test_returns_empty_for_blank(self) -> None:
        self.assertEqual(parse_changelog(''), {})

    def test_extracts_versions_and_bullets(self) -> None:
        parsed = parse_changelog(SAMPLE)
        self.assertEqual(set(parsed.keys()), {'1.3.0', '1.2.0', '1.1.0'})
        self.assertEqual(parsed['1.3.0'], ['new shiny', 'another bullet'])
        self.assertEqual(parsed['1.2.0'], ['mid bullet'])

    def test_skips_versions_without_bullets(self) -> None:
        parsed = parse_changelog('# X\n\n## 1.0.0\nplain text\n')
        self.assertEqual(parsed, {})


class RecentNotesTest(unittest.TestCase):
    def test_returns_only_newer_versions(self) -> None:
        notes = get_recent_release_notes('1.3.0', '1.2.0', SAMPLE)
        self.assertEqual(notes, ['new shiny', 'another bullet'])

    def test_first_run_returns_all(self) -> None:
        notes = get_recent_release_notes('1.3.0', None, SAMPLE)
        self.assertEqual(notes[0], 'new shiny')
        self.assertIn('oldest bullet', notes)

    def test_no_new_when_at_or_below_previous(self) -> None:
        self.assertEqual(get_recent_release_notes('1.1.0', '1.3.0', SAMPLE), [])

    def test_caps_at_max_shown(self) -> None:
        big_changelog = '# Changelog\n\n' + ''.join(
            f'## 9.9.{i}\n- bullet {i}\n\n' for i in range(20)
        )
        notes = get_recent_release_notes('9.9.19', '0.0.1', big_changelog)
        self.assertEqual(len(notes), MAX_RELEASE_NOTES_SHOWN)


class AllNotesTest(unittest.TestCase):
    def test_sorted_oldest_first(self) -> None:
        all_notes = get_all_release_notes(SAMPLE)
        versions = [version for version, _ in all_notes]
        self.assertEqual(versions, ['1.1.0', '1.2.0', '1.3.0'])


class ReadLocalChangelogTest(unittest.TestCase):
    def test_reads_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'CHANGELOG.md').write_text(SAMPLE, encoding='utf-8')
            self.assertIn('## 1.3.0', read_local_changelog(Path(tmp)))

    def test_returns_empty_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(read_local_changelog(Path(tmp)), '')


class CheckForReleaseNotesTest(unittest.TestCase):
    def test_signals_when_changelog_present_and_newer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'CHANGELOG.md').write_text(SAMPLE, encoding='utf-8')
            payload = check_for_release_notes('1.3.0', '1.2.0', cwd=Path(tmp))
        self.assertTrue(payload['hasReleaseNotes'])
        self.assertEqual(payload['releaseNotes'][0], 'new shiny')

    def test_silent_when_missing_changelog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = check_for_release_notes('1.3.0', None, cwd=Path(tmp))
        self.assertFalse(payload['hasReleaseNotes'])
        self.assertEqual(payload['releaseNotes'], [])


if __name__ == '__main__':
    unittest.main()
