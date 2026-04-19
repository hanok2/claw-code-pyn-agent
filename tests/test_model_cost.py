"""Tests for model pricing utilities ported from utils/modelCost.ts."""

from __future__ import annotations

import unittest

from src.model_cost import (
    COST_HAIKU_35,
    COST_HAIKU_45,
    COST_TIER_3_15,
    COST_TIER_5_25,
    COST_TIER_15_75,
    COST_TIER_30_150,
    DEFAULT_UNKNOWN_MODEL_COST,
    calculate_cost_from_tokens,
    calculate_usd_cost,
    format_model_pricing,
    get_model_costs,
    get_model_pricing_string,
    get_opus_4_6_cost_tier,
    tokens_to_usd_cost,
)


class TierConstantsTest(unittest.TestCase):
    def test_sonnet_tier(self) -> None:
        self.assertEqual(COST_TIER_3_15.input_tokens, 3.0)
        self.assertEqual(COST_TIER_3_15.output_tokens, 15.0)

    def test_opus_4_tier(self) -> None:
        self.assertEqual(COST_TIER_15_75.input_tokens, 15.0)

    def test_opus_4_5_tier(self) -> None:
        self.assertEqual(COST_TIER_5_25.input_tokens, 5.0)

    def test_fast_mode_tier(self) -> None:
        self.assertEqual(COST_TIER_30_150.input_tokens, 30.0)

    def test_haiku_tiers(self) -> None:
        self.assertAlmostEqual(COST_HAIKU_35.input_tokens, 0.8)
        self.assertEqual(COST_HAIKU_45.input_tokens, 1.0)


class GetModelCostsTest(unittest.TestCase):
    def test_opus_4_6_default(self) -> None:
        self.assertIs(get_model_costs('claude-opus-4-6'), COST_TIER_5_25)

    def test_opus_4_6_fast_mode(self) -> None:
        self.assertIs(
            get_model_costs('claude-opus-4-6', fast_mode=True),
            COST_TIER_30_150,
        )

    def test_versioned_model_name_resolves(self) -> None:
        self.assertIs(
            get_model_costs('claude-opus-4-6-20251015'),
            COST_TIER_5_25,
        )

    def test_sonnet_models_use_3_15(self) -> None:
        for name in ('claude-sonnet-4-6', 'claude-sonnet-4-5', 'claude-sonnet-4'):
            self.assertIs(get_model_costs(name), COST_TIER_3_15)

    def test_opus_4_and_4_1_use_15_75(self) -> None:
        self.assertIs(get_model_costs('claude-opus-4'), COST_TIER_15_75)
        self.assertIs(get_model_costs('claude-opus-4-1'), COST_TIER_15_75)

    def test_haiku_4_5(self) -> None:
        self.assertIs(get_model_costs('claude-haiku-4-5-20251001'), COST_HAIKU_45)

    def test_haiku_3_5(self) -> None:
        self.assertIs(get_model_costs('claude-3-5-haiku-20241022'), COST_HAIKU_35)

    def test_unknown_falls_back_to_default(self) -> None:
        self.assertIs(get_model_costs('mystery-llm-3000'), DEFAULT_UNKNOWN_MODEL_COST)

    def test_get_opus_4_6_helper_matches_fast_mode(self) -> None:
        self.assertIs(get_opus_4_6_cost_tier(False), COST_TIER_5_25)
        self.assertIs(get_opus_4_6_cost_tier(True), COST_TIER_30_150)


class TokensToUsdCostTest(unittest.TestCase):
    def test_simple_input_output(self) -> None:
        cost = tokens_to_usd_cost(
            COST_TIER_3_15, input_tokens=1_000_000, output_tokens=500_000,
        )
        self.assertAlmostEqual(cost, 3.0 + 7.5)

    def test_includes_cache_tokens(self) -> None:
        cost = tokens_to_usd_cost(
            COST_TIER_3_15,
            input_tokens=0,
            output_tokens=0,
            cache_read_input_tokens=1_000_000,
            cache_creation_input_tokens=1_000_000,
        )
        self.assertAlmostEqual(
            cost,
            COST_TIER_3_15.prompt_cache_read_tokens
            + COST_TIER_3_15.prompt_cache_write_tokens,
        )

    def test_includes_web_search(self) -> None:
        cost = tokens_to_usd_cost(
            COST_TIER_3_15,
            input_tokens=0,
            output_tokens=0,
            web_search_requests=10,
        )
        self.assertAlmostEqual(cost, 0.10)


class CalculateUsdCostTest(unittest.TestCase):
    def test_resolves_model_then_costs(self) -> None:
        cost = calculate_usd_cost(
            'claude-sonnet-4-6',
            input_tokens=1_000_000,
            output_tokens=500_000,
        )
        self.assertAlmostEqual(cost, 10.5)

    def test_fast_mode_changes_opus_46_cost(self) -> None:
        normal = calculate_usd_cost(
            'claude-opus-4-6', input_tokens=1_000_000, output_tokens=0,
        )
        fast = calculate_usd_cost(
            'claude-opus-4-6', input_tokens=1_000_000, output_tokens=0,
            fast_mode=True,
        )
        self.assertGreater(fast, normal)
        self.assertAlmostEqual(normal, 5.0)
        self.assertAlmostEqual(fast, 30.0)


class CalculateCostFromTokensTest(unittest.TestCase):
    def test_camel_case_dict_input(self) -> None:
        cost = calculate_cost_from_tokens(
            'claude-opus-4-1',
            {
                'inputTokens': 1_000_000,
                'outputTokens': 0,
                'cacheReadInputTokens': 0,
                'cacheCreationInputTokens': 0,
            },
        )
        self.assertAlmostEqual(cost, 15.0)


class FormatPricingTest(unittest.TestCase):
    def test_integers_no_decimals(self) -> None:
        self.assertEqual(format_model_pricing(COST_TIER_3_15), '$3/$15 per Mtok')

    def test_haiku_decimals(self) -> None:
        self.assertEqual(format_model_pricing(COST_HAIKU_35), '$0.80/$4 per Mtok')

    def test_get_pricing_string_known(self) -> None:
        self.assertEqual(
            get_model_pricing_string('claude-opus-4-6'),
            '$5/$25 per Mtok',
        )

    def test_get_pricing_string_unknown(self) -> None:
        self.assertIsNone(get_model_pricing_string('unknown-model'))


if __name__ == '__main__':
    unittest.main()
