"""Tests for SDK core types ported from entrypoints/sdk/coreTypes.ts."""

from __future__ import annotations

import unittest

from src.sdk_core_types import (
    API_KEY_SOURCES,
    CONFIG_SCOPES,
    EXIT_REASONS,
    HOOK_EVENTS,
    SDK_BETAS,
    JsonSchemaOutputFormat,
    McpClaudeAIProxyServerConfig,
    McpHttpServerConfig,
    McpSdkServerConfig,
    McpSSEServerConfig,
    McpStdioServerConfig,
    ModelUsage,
    ThinkingAdaptive,
    ThinkingDisabled,
    ThinkingEnabled,
    mcp_server_config_from_dict,
    thinking_config_from_dict,
)


class HookEventsTest(unittest.TestCase):
    def test_includes_known_events(self) -> None:
        for required in (
            'PreToolUse',
            'PostToolUse',
            'UserPromptSubmit',
            'SessionStart',
            'PreCompact',
            'WorktreeCreate',
            'CwdChanged',
            'FileChanged',
        ):
            self.assertIn(required, HOOK_EVENTS)

    def test_no_duplicates(self) -> None:
        self.assertEqual(len(HOOK_EVENTS), len(set(HOOK_EVENTS)))


class ExitReasonsTest(unittest.TestCase):
    def test_known_exit_reasons(self) -> None:
        for required in (
            'clear', 'resume', 'logout', 'prompt_input_exit',
            'other', 'bypass_permissions_disabled',
        ):
            self.assertIn(required, EXIT_REASONS)


class EnumLiteralsTest(unittest.TestCase):
    def test_api_key_sources(self) -> None:
        self.assertEqual(set(API_KEY_SOURCES), {'user', 'project', 'org', 'temporary', 'oauth'})

    def test_config_scopes(self) -> None:
        self.assertEqual(set(CONFIG_SCOPES), {'local', 'user', 'project'})

    def test_sdk_betas_known(self) -> None:
        self.assertIn('context-1m-2025-08-07', SDK_BETAS)


class ModelUsageTest(unittest.TestCase):
    def test_round_trip(self) -> None:
        raw = {
            'inputTokens': 100, 'outputTokens': 50,
            'cacheReadInputTokens': 10, 'cacheCreationInputTokens': 5,
            'webSearchRequests': 0, 'costUSD': 0.001,
            'contextWindow': 200000, 'maxOutputTokens': 8192,
        }
        usage = ModelUsage.from_dict(raw)
        self.assertEqual(usage.input_tokens, 100)
        self.assertEqual(usage.cost_usd, 0.001)
        self.assertEqual(usage.to_dict(), raw)


class ThinkingConfigTest(unittest.TestCase):
    def test_adaptive(self) -> None:
        cfg = thinking_config_from_dict({'type': 'adaptive'})
        self.assertIsInstance(cfg, ThinkingAdaptive)
        self.assertEqual(cfg.to_dict(), {'type': 'adaptive'})

    def test_enabled_with_budget(self) -> None:
        cfg = thinking_config_from_dict({'type': 'enabled', 'budgetTokens': 1024})
        self.assertIsInstance(cfg, ThinkingEnabled)
        self.assertEqual(cfg.to_dict(), {'type': 'enabled', 'budgetTokens': 1024})

    def test_enabled_without_budget(self) -> None:
        cfg = thinking_config_from_dict({'type': 'enabled'})
        self.assertEqual(cfg.to_dict(), {'type': 'enabled'})

    def test_disabled(self) -> None:
        cfg = thinking_config_from_dict({'type': 'disabled'})
        self.assertIsInstance(cfg, ThinkingDisabled)

    def test_unknown_type_raises(self) -> None:
        with self.assertRaises(ValueError):
            thinking_config_from_dict({'type': 'something-else'})


class McpServerConfigTest(unittest.TestCase):
    def test_stdio_default_type(self) -> None:
        cfg = mcp_server_config_from_dict({'command': 'npx'})
        self.assertIsInstance(cfg, McpStdioServerConfig)
        self.assertEqual(cfg.command, 'npx')

    def test_stdio_with_args_env(self) -> None:
        cfg = mcp_server_config_from_dict({
            'type': 'stdio',
            'command': 'node',
            'args': ['./mcp.js'],
            'env': {'TOKEN': 'xyz'},
        })
        out = cfg.to_dict()
        self.assertEqual(out['command'], 'node')
        self.assertEqual(out['args'], ['./mcp.js'])
        self.assertEqual(out['env'], {'TOKEN': 'xyz'})

    def test_sse(self) -> None:
        cfg = mcp_server_config_from_dict({'type': 'sse', 'url': 'https://x.example'})
        self.assertIsInstance(cfg, McpSSEServerConfig)

    def test_http_with_headers(self) -> None:
        cfg = mcp_server_config_from_dict({
            'type': 'http',
            'url': 'https://x.example',
            'headers': {'Auth': 'Bearer 1'},
        })
        self.assertIsInstance(cfg, McpHttpServerConfig)
        self.assertEqual(cfg.headers, {'Auth': 'Bearer 1'})

    def test_sdk(self) -> None:
        cfg = mcp_server_config_from_dict({'type': 'sdk', 'name': 'my-sdk'})
        self.assertIsInstance(cfg, McpSdkServerConfig)

    def test_claudeai_proxy(self) -> None:
        cfg = mcp_server_config_from_dict({
            'type': 'claudeai-proxy',
            'url': 'https://claude.ai/p',
            'id': 'abc',
        })
        self.assertIsInstance(cfg, McpClaudeAIProxyServerConfig)

    def test_unknown_type_raises(self) -> None:
        with self.assertRaises(ValueError):
            mcp_server_config_from_dict({'type': 'mystery'})

    def test_stdio_requires_command(self) -> None:
        with self.assertRaises(ValueError):
            mcp_server_config_from_dict({'type': 'stdio'})


class JsonSchemaOutputFormatTest(unittest.TestCase):
    def test_round_trip(self) -> None:
        fmt = JsonSchemaOutputFormat.from_dict({
            'type': 'json_schema',
            'schema': {'type': 'object', 'properties': {}},
        })
        self.assertEqual(fmt.schema['type'], 'object')
        self.assertEqual(fmt.to_dict()['type'], 'json_schema')

    def test_rejects_wrong_type(self) -> None:
        with self.assertRaises(ValueError):
            JsonSchemaOutputFormat.from_dict({'type': 'text', 'schema': {}})

    def test_requires_schema_mapping(self) -> None:
        with self.assertRaises(ValueError):
            JsonSchemaOutputFormat.from_dict({'type': 'json_schema'})


if __name__ == '__main__':
    unittest.main()
