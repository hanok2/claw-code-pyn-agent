"""Tests for ``src/format_utils.py``."""

from __future__ import annotations

import unittest

from src.format_utils import (
    format_duration,
    format_file_size,
    format_number,
    format_seconds_short,
    format_tokens,
)


class FormatFileSizeTest(unittest.TestCase):
    def test_bytes(self) -> None:
        self.assertEqual(format_file_size(0), '0 bytes')
        self.assertEqual(format_file_size(512), '512 bytes')

    def test_kb_with_decimal(self) -> None:
        self.assertEqual(format_file_size(1536), '1.5KB')

    def test_kb_trims_trailing_zero(self) -> None:
        self.assertEqual(format_file_size(2048), '2KB')

    def test_mb(self) -> None:
        self.assertEqual(format_file_size(5 * 1024 * 1024), '5MB')

    def test_gb(self) -> None:
        self.assertEqual(format_file_size(2 * 1024 * 1024 * 1024), '2GB')


class FormatSecondsShortTest(unittest.TestCase):
    def test_basic(self) -> None:
        self.assertEqual(format_seconds_short(1234), '1.2s')

    def test_under_one(self) -> None:
        self.assertEqual(format_seconds_short(450), '0.5s')


class FormatDurationTest(unittest.TestCase):
    def test_zero(self) -> None:
        self.assertEqual(format_duration(0), '0s')

    def test_sub_second(self) -> None:
        self.assertEqual(format_duration(0.5), '0.0s')

    def test_seconds_only(self) -> None:
        self.assertEqual(format_duration(5_000), '5s')

    def test_minutes_seconds(self) -> None:
        self.assertEqual(format_duration(125_000), '2m 5s')

    def test_hours(self) -> None:
        self.assertEqual(format_duration(3_725_000), '1h 2m 5s')

    def test_days(self) -> None:
        # 1d 2h 3m
        ms = 86_400_000 + 2 * 3_600_000 + 3 * 60_000 + 0
        self.assertEqual(format_duration(ms), '1d 2h 3m')

    def test_hide_trailing_zeros_minutes(self) -> None:
        self.assertEqual(
            format_duration(120_000, hide_trailing_zeros=True), '2m',
        )

    def test_hide_trailing_zeros_hours(self) -> None:
        self.assertEqual(
            format_duration(3_600_000, hide_trailing_zeros=True), '1h',
        )

    def test_most_significant_only_picks_largest_unit(self) -> None:
        self.assertEqual(format_duration(125_000, most_significant_only=True), '2m')
        self.assertEqual(
            format_duration(3_725_000, most_significant_only=True), '1h',
        )

    def test_rounding_carry_over(self) -> None:
        # 59,500 ms rounds seconds=60 → carries to 1m 0s
        self.assertEqual(format_duration(59_500 + 60_000), '2m 0s')


class FormatNumberTest(unittest.TestCase):
    def test_below_thousand(self) -> None:
        self.assertEqual(format_number(900), '900')
        self.assertEqual(format_number(0), '0')

    def test_thousands_with_decimal(self) -> None:
        self.assertEqual(format_number(1321), '1.3k')

    def test_thousand_keeps_decimal(self) -> None:
        self.assertEqual(format_number(1000), '1.0k')

    def test_millions(self) -> None:
        self.assertEqual(format_number(2_500_000), '2.5m')

    def test_billions(self) -> None:
        self.assertEqual(format_number(3_700_000_000), '3.7b')


class FormatTokensTest(unittest.TestCase):
    def test_trims_decimal_zero(self) -> None:
        self.assertEqual(format_tokens(1000), '1k')

    def test_keeps_meaningful_decimal(self) -> None:
        self.assertEqual(format_tokens(1321), '1.3k')

    def test_below_thousand(self) -> None:
        self.assertEqual(format_tokens(450), '450')


if __name__ == '__main__':
    unittest.main()
