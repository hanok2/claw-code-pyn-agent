"""Tests for sandbox configuration types ported from sandboxTypes.ts."""

from __future__ import annotations

import unittest

from src.sandbox_types import (
    SandboxFilesystemConfig,
    SandboxNetworkConfig,
    SandboxRipgrepConfig,
    SandboxSettings,
)


class SandboxNetworkConfigTest(unittest.TestCase):
    def test_round_trip(self) -> None:
        raw = {
            'allowedDomains': ['example.com'],
            'allowManagedDomainsOnly': True,
            'allowUnixSockets': ['/tmp/sock'],
            'allowAllUnixSockets': False,
            'allowLocalBinding': True,
            'httpProxyPort': 8080,
            'socksProxyPort': 1080,
        }
        parsed = SandboxNetworkConfig.from_dict(raw)
        self.assertEqual(parsed.allowed_domains, ['example.com'])
        self.assertEqual(parsed.http_proxy_port, 8080)
        self.assertEqual(parsed.to_dict(), raw)

    def test_strips_none(self) -> None:
        parsed = SandboxNetworkConfig.from_dict({'allowedDomains': ['a']})
        self.assertEqual(parsed.to_dict(), {'allowedDomains': ['a']})

    def test_rejects_wrong_type(self) -> None:
        with self.assertRaises(ValueError):
            SandboxNetworkConfig.from_dict({'allowedDomains': 'nope'})


class SandboxFilesystemConfigTest(unittest.TestCase):
    def test_round_trip(self) -> None:
        raw = {
            'allowWrite': ['/tmp'],
            'denyWrite': ['/etc'],
            'denyRead': ['/etc/secrets'],
            'allowRead': ['/etc/secrets/public'],
            'allowManagedReadPathsOnly': False,
        }
        parsed = SandboxFilesystemConfig.from_dict(raw)
        self.assertEqual(parsed.allow_write, ['/tmp'])
        self.assertEqual(parsed.to_dict(), raw)


class SandboxRipgrepConfigTest(unittest.TestCase):
    def test_requires_command(self) -> None:
        with self.assertRaises(ValueError):
            SandboxRipgrepConfig.from_dict({'args': ['-i']})

    def test_round_trip(self) -> None:
        parsed = SandboxRipgrepConfig.from_dict({'command': 'rg', 'args': ['--no-ignore']})
        self.assertEqual(parsed.command, 'rg')
        self.assertEqual(parsed.to_dict(), {'command': 'rg', 'args': ['--no-ignore']})


class SandboxSettingsTest(unittest.TestCase):
    def test_full_round_trip_preserves_passthrough(self) -> None:
        raw = {
            'enabled': True,
            'failIfUnavailable': False,
            'autoAllowBashIfSandboxed': True,
            'allowUnsandboxedCommands': True,
            'network': {'allowedDomains': ['x.com']},
            'filesystem': {'allowWrite': ['/tmp']},
            'ignoreViolations': {'NetworkViolation': ['y.com']},
            'enableWeakerNestedSandbox': False,
            'enableWeakerNetworkIsolation': False,
            'excludedCommands': ['rm -rf /'],
            'ripgrep': {'command': 'rg'},
            'enabledPlatforms': ['macos'],
            'somethingFuture': 42,
        }
        parsed = SandboxSettings.from_dict(raw)
        self.assertTrue(parsed.enabled)
        self.assertEqual(parsed.network.allowed_domains, ['x.com'])
        self.assertEqual(parsed.ignore_violations, {'NetworkViolation': ['y.com']})
        self.assertEqual(parsed.extra['enabledPlatforms'], ['macos'])
        self.assertEqual(parsed.extra['somethingFuture'], 42)

        back = parsed.to_dict()
        self.assertEqual(back['enabled'], True)
        self.assertEqual(back['enabledPlatforms'], ['macos'])
        self.assertEqual(back['somethingFuture'], 42)

    def test_empty_returns_defaults(self) -> None:
        parsed = SandboxSettings.from_dict({})
        self.assertIsNone(parsed.enabled)
        self.assertIsNone(parsed.network)
        self.assertEqual(parsed.to_dict(), {})

    def test_rejects_non_mapping(self) -> None:
        with self.assertRaises(ValueError):
            SandboxSettings.from_dict('nope')  # type: ignore[arg-type]

    def test_ignore_violations_must_be_mapping(self) -> None:
        with self.assertRaises(ValueError):
            SandboxSettings.from_dict({'ignoreViolations': ['nope']})


if __name__ == '__main__':
    unittest.main()
