"""web_fetch refuses binary payloads instead of returning UTF-8 garbage.

The original code decoded all responses with `errors='replace'`, which
turns a PDF into Unicode replacement-char soup. The model reads that
garbage and fills the gaps with hallucinated content. Pin the refusal so
this regression is observable.
"""
from __future__ import annotations

import io
import unittest
from pathlib import Path
from unittest.mock import patch

from src.agent_tools import (
    ToolExecutionError,
    _looks_binary,
    _web_fetch,
    build_tool_context,
    default_tool_registry,
)
from src.agent_types import AgentPermissions, AgentRuntimeConfig


class _FakeResponse:
    def __init__(self, body: bytes, content_type: str):
        self._body = body
        self.headers = _FakeHeaders(content_type)

    def read(self, n: int) -> bytes:
        return self._body[:n]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return None


class _FakeHeaders:
    def __init__(self, ct: str):
        self._ct = ct

    def get_content_type(self) -> str:
        return self._ct


def _ctx(tmp: str):
    return build_tool_context(
        AgentRuntimeConfig(
            cwd=Path(tmp),
            permissions=AgentPermissions(
                allow_shell_commands=False, allow_destructive_shell_commands=False,
            ),
        ),
        tool_registry=default_tool_registry(),
    )


class TestLooksBinary(unittest.TestCase):
    def test_pdf_magic_bytes_detected(self):
        assert _looks_binary(b'%PDF-1.4\nblah\nblah', 'application/octet-stream')
        assert _looks_binary(b'%PDF-1.4\nblah', None)

    def test_application_pdf_content_type_detected(self):
        # Even without magic bytes (rare but possible).
        assert _looks_binary(b'whatever', 'application/pdf')

    def test_image_content_type_detected(self):
        assert _looks_binary(b'fakejpg', 'image/jpeg')

    def test_charset_suffix_does_not_break_detection(self):
        assert _looks_binary(b'%PDF-stuff', 'application/pdf; charset=binary')

    def test_nul_byte_detected(self):
        assert _looks_binary(b'hello\x00world\x00\x00', 'text/plain')

    def test_clean_text_passes(self):
        assert not _looks_binary(b'hello world\nthis is utf-8 prose.', 'text/html')

    def test_high_nonprintable_ratio_detected(self):
        # >10% bytes outside printable ASCII range
        body = bytes(range(0, 200))  # ~50% non-printable
        assert _looks_binary(body, 'text/plain')

    def test_empty_body_not_binary(self):
        assert not _looks_binary(b'', 'text/plain')


class TestWebFetchBinaryRefusal(unittest.TestCase):
    def test_pdf_fetch_raises_with_named_reason(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _ctx(tmp)
            fake_pdf = b'%PDF-1.4\n' + bytes(range(256)) * 10
            with patch(
                'urllib.request.urlopen',
                return_value=_FakeResponse(fake_pdf, 'application/pdf'),
            ):
                with self.assertRaises(ToolExecutionError) as cm:
                    _web_fetch({'url': 'https://example.com/paper.pdf'}, ctx)
                msg = str(cm.exception)
                self.assertIn('non-text content', msg)
                self.assertIn('Do NOT proceed as if', msg)

    def test_html_fetch_succeeds(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _ctx(tmp)
            html = b'<html><body><p>Hello, world.</p></body></html>'
            with patch(
                'urllib.request.urlopen',
                return_value=_FakeResponse(html, 'text/html'),
            ):
                result = _web_fetch({'url': 'https://example.com/'}, ctx)
                # _web_fetch returns a tuple (text, metadata); the runtime
                # unwraps it. We just confirm it returned text containing
                # the body, not a raised exception.
                if isinstance(result, tuple):
                    text = result[0]
                else:
                    text = result
                self.assertIn('Hello, world.', text)


if __name__ == '__main__':
    unittest.main()
