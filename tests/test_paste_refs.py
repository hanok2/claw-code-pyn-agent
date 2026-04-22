"""Unit tests for :mod:`src.paste_refs`.

Mirrors the npm ``src/history.ts`` test expectations: line counting reports
``\\n`` separators (not lines), reference ids of ``0`` are ignored, and
expansion processes references back-to-front so spliced content cannot shift
later offsets.
"""

from __future__ import annotations

import unittest

from src.paste_refs import (
    PastedContent,
    expand_pasted_text_refs,
    format_image_ref,
    format_pasted_text_ref,
    get_pasted_text_ref_num_lines,
    parse_references,
)


class GetPastedTextRefNumLinesTests(unittest.TestCase):
    def test_empty_text_reports_zero(self) -> None:
        self.assertEqual(get_pasted_text_ref_num_lines(''), 0)

    def test_single_line_reports_zero(self) -> None:
        self.assertEqual(get_pasted_text_ref_num_lines('hello'), 0)

    def test_three_lines_separated_by_lf_reports_two(self) -> None:
        # Matches the npm convention: count of separators, not lines.
        self.assertEqual(get_pasted_text_ref_num_lines('a\nb\nc'), 2)

    def test_crlf_counted_as_one_separator(self) -> None:
        self.assertEqual(get_pasted_text_ref_num_lines('a\r\nb\r\nc'), 2)

    def test_lone_cr_counted_as_separator(self) -> None:
        self.assertEqual(get_pasted_text_ref_num_lines('a\rb'), 1)


class FormatRefTests(unittest.TestCase):
    def test_zero_lines_omits_suffix(self) -> None:
        self.assertEqual(format_pasted_text_ref(1, 0), '[Pasted text #1]')

    def test_nonzero_lines_includes_suffix(self) -> None:
        self.assertEqual(
            format_pasted_text_ref(7, 42), '[Pasted text #7 +42 lines]'
        )

    def test_image_ref_format(self) -> None:
        self.assertEqual(format_image_ref(3), '[Image #3]')


class ParseReferencesTests(unittest.TestCase):
    def test_finds_pasted_text_ref(self) -> None:
        refs = parse_references('see [Pasted text #2 +5 lines] please')
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].id, 2)
        self.assertEqual(refs[0].match, '[Pasted text #2 +5 lines]')
        self.assertEqual(refs[0].index, 4)

    def test_finds_pasted_text_ref_without_line_suffix(self) -> None:
        refs = parse_references('[Pasted text #1]')
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].id, 1)

    def test_finds_image_ref(self) -> None:
        refs = parse_references('[Image #4]')
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].id, 4)

    def test_finds_truncated_ref(self) -> None:
        refs = parse_references('[...Truncated text #9 +200 lines]')
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].id, 9)

    def test_ignores_zero_id(self) -> None:
        self.assertEqual(parse_references('[Pasted text #0]'), [])

    def test_finds_multiple_refs_in_order(self) -> None:
        refs = parse_references('a [Pasted text #1] b [Image #2] c')
        self.assertEqual([r.id for r in refs], [1, 2])
        # Indexes increase with the position of the match.
        self.assertLess(refs[0].index, refs[1].index)

    def test_ignores_non_ref_brackets(self) -> None:
        self.assertEqual(parse_references('[not a ref] [pasted text #1]'), [])


class ExpandPastedTextRefsTests(unittest.TestCase):
    def _store(self, *items: PastedContent) -> dict[int, PastedContent]:
        return {item.id: item for item in items}

    def test_substitutes_text_content(self) -> None:
        store = self._store(PastedContent(id=1, type='text', content='HELLO'))
        result = expand_pasted_text_refs('start [Pasted text #1] end', store)
        self.assertEqual(result, 'start HELLO end')

    def test_leaves_unknown_ids_alone(self) -> None:
        result = expand_pasted_text_refs('keep [Pasted text #1]', {})
        self.assertEqual(result, 'keep [Pasted text #1]')

    def test_skips_image_entries(self) -> None:
        store = self._store(
            PastedContent(id=1, type='image', content='base64', media_type='image/png')
        )
        result = expand_pasted_text_refs('look [Image #1]', store)
        self.assertEqual(result, 'look [Image #1]')

    def test_reverse_splice_preserves_offsets(self) -> None:
        # If we spliced front-to-back, replacing #1 with a longer string would
        # invalidate the recorded index of #2.  The reverse-splice contract
        # guarantees both substitutions land in the right place.
        store = self._store(
            PastedContent(id=1, type='text', content='LONG_REPLACEMENT_VALUE'),
            PastedContent(id=2, type='text', content='B'),
        )
        result = expand_pasted_text_refs(
            '[Pasted text #1] middle [Pasted text #2]', store
        )
        self.assertEqual(result, 'LONG_REPLACEMENT_VALUE middle B')

    def test_substituted_content_with_ref_like_string_is_not_re_expanded(self) -> None:
        # If we processed front-to-back and re-scanned, the substituted
        # content's literal "[Pasted text #2]" could be picked up as a real
        # ref.  Reverse-splice avoids that because we never re-parse.
        store = self._store(
            PastedContent(id=1, type='text', content='contains [Pasted text #2]'),
            PastedContent(id=2, type='text', content='SHOULD_NOT_APPEAR'),
        )
        result = expand_pasted_text_refs('[Pasted text #1]', store)
        self.assertEqual(result, 'contains [Pasted text #2]')

    def test_text_with_no_refs_returns_unchanged(self) -> None:
        self.assertEqual(expand_pasted_text_refs('plain text', {}), 'plain text')


if __name__ == '__main__':
    unittest.main()
