"""Tests for the bundled small utilities ported in ``src/small_utils.py``."""

from __future__ import annotations

import unittest

from src.small_utils import (
    count,
    create_agent_id,
    difference,
    escape_xml,
    escape_xml_attr,
    every_in,
    intersects,
    intersperse,
    object_group_by,
    union,
    uniq,
    validate_uuid,
)


class IntersperseTest(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(intersperse([], lambda i: ','), [])

    def test_single_item_no_separator(self) -> None:
        self.assertEqual(intersperse(['a'], lambda i: ','), ['a'])

    def test_separator_receives_index_starting_at_one(self) -> None:
        seen: list[int] = []

        def sep(i: int) -> str:
            seen.append(i)
            return f'-{i}-'

        out = intersperse(['a', 'b', 'c'], sep)
        self.assertEqual(out, ['a', '-1-', 'b', '-2-', 'c'])
        self.assertEqual(seen, [1, 2])


class CountTest(unittest.TestCase):
    def test_counts_truthy(self) -> None:
        self.assertEqual(count([1, 2, 3, 4], lambda x: x % 2 == 0), 2)

    def test_predicate_returning_objects_treated_as_truthy(self) -> None:
        self.assertEqual(count(['', 'x', 'y'], lambda s: s), 2)


class UniqTest(unittest.TestCase):
    def test_preserves_first_seen_order(self) -> None:
        self.assertEqual(uniq([3, 1, 2, 1, 3, 4]), [3, 1, 2, 4])


class ObjectGroupByTest(unittest.TestCase):
    def test_groups_by_key(self) -> None:
        out = object_group_by(['apple', 'banana', 'avocado'], lambda s, _i: s[0])
        self.assertEqual(out, {'a': ['apple', 'avocado'], 'b': ['banana']})

    def test_passes_index_to_selector(self) -> None:
        out = object_group_by(
            ['x', 'y', 'z'], lambda _s, i: 'even' if i % 2 == 0 else 'odd',
        )
        self.assertEqual(out, {'even': ['x', 'z'], 'odd': ['y']})


class SetOpsTest(unittest.TestCase):
    def test_difference(self) -> None:
        self.assertEqual(difference({1, 2, 3}, {2}), {1, 3})

    def test_intersects_true(self) -> None:
        self.assertTrue(intersects({1, 2}, {2, 3}))

    def test_intersects_false(self) -> None:
        self.assertFalse(intersects({1, 2}, {3, 4}))

    def test_intersects_empty_short_circuits(self) -> None:
        self.assertFalse(intersects(set(), {1}))
        self.assertFalse(intersects({1}, set()))

    def test_every_in(self) -> None:
        self.assertTrue(every_in({1, 2}, {1, 2, 3}))
        self.assertFalse(every_in({1, 4}, {1, 2, 3}))
        self.assertTrue(every_in(set(), {1, 2}))

    def test_union(self) -> None:
        self.assertEqual(union({1, 2}, {2, 3}), {1, 2, 3})


class XmlEscapeTest(unittest.TestCase):
    def test_escape_xml(self) -> None:
        self.assertEqual(
            escape_xml('a & b < c > d'), 'a &amp; b &lt; c &gt; d',
        )

    def test_escape_xml_amp_first_no_double_escape(self) -> None:
        self.assertEqual(escape_xml('<&>'), '&lt;&amp;&gt;')

    def test_escape_xml_attr_includes_quotes(self) -> None:
        self.assertEqual(
            escape_xml_attr('he said "hi" & \'bye\''),
            'he said &quot;hi&quot; &amp; &apos;bye&apos;',
        )


class ValidateUuidTest(unittest.TestCase):
    def test_valid_lowercase(self) -> None:
        u = '12345678-1234-1234-1234-123456789012'
        self.assertEqual(validate_uuid(u), u)

    def test_valid_uppercase(self) -> None:
        u = 'ABCDEF12-1234-5678-90AB-CDEF12345678'
        self.assertEqual(validate_uuid(u), u)

    def test_invalid_format(self) -> None:
        self.assertIsNone(validate_uuid('not-a-uuid'))

    def test_non_string_returns_none(self) -> None:
        self.assertIsNone(validate_uuid(123))
        self.assertIsNone(validate_uuid(None))


class CreateAgentIdTest(unittest.TestCase):
    def test_no_label(self) -> None:
        agent_id = create_agent_id()
        self.assertRegex(agent_id, r'^a[0-9a-f]{16}$')

    def test_with_label(self) -> None:
        agent_id = create_agent_id('compact')
        self.assertRegex(agent_id, r'^acompact-[0-9a-f]{16}$')

    def test_unique_across_calls(self) -> None:
        ids = {create_agent_id() for _ in range(50)}
        self.assertEqual(len(ids), 50)


if __name__ == '__main__':
    unittest.main()
