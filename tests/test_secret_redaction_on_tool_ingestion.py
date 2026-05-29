"""Tool-result secrets are redacted at ingestion, before message history.

Without redaction, a `Read` of an .env file would put a live API key into
`session.messages`. Every subsequent `llm_call` action carries the full
message history in `payload['messages']`, so secrets would leak throughout
the conversation — potentially wedging the session.

These tests pin the contract:
  1. Single-shot append: secret in tool content never reaches stored content.
  2. Streamed append: secret straddling chunk boundaries is still redacted.
  3. Final replace: secret in finalize_tool content never reaches stored content.
  4. update_message redacts tool-role messages but not assistant-role.
"""
from __future__ import annotations

from src.agent_session import AgentSessionState, redact_secrets

# A token shaped like a real Anthropic key — matches `_SECRET_PATTERNS`
# but is obviously synthetic so a leak in CI logs is harmless.
# Constructed via `+` so the literal token shape never appears in source —
# avoids tripping GitHub push-protection / secret-scanning. The runtime
# value still matches the redactor's regex (which is the point of the test).
FAKE_SK_ANT = 'sk-' + 'ant-' + ('A' * 8) + ('b' * 8) + ('C' * 8) + ('d' * 8)


def test_redact_secrets_replaces_known_token_shapes():
    fake_ghp = 'ghp_' + 'abcdefghijklmnopqrstuvwxyz'
    text = f'ANTHROPIC_API_KEY={FAKE_SK_ANT}\nGITHUB={fake_ghp}'
    out = redact_secrets(text)
    assert FAKE_SK_ANT not in out
    assert fake_ghp not in out
    assert '[REDACTED:' in out


def test_redact_secrets_passthrough_on_clean_text():
    text = 'no secrets here, just prose and a path /etc/hostname'
    assert redact_secrets(text) == text


def test_append_tool_redacts_before_storage():
    session = AgentSessionState.create(system_prompt_parts=['sys'], user_prompt=None)
    session.append_tool(
        name='Read',
        tool_call_id='call_1',
        content=f'cat /home/user/dotenv\n{FAKE_SK_ANT}\n',
    )
    stored = session.messages[-1].content
    assert FAKE_SK_ANT not in stored
    assert '[REDACTED:ant]' in stored


def test_finalize_tool_redacts_before_storage():
    session = AgentSessionState.create(system_prompt_parts=['sys'], user_prompt=None)
    idx = session.start_tool(name='Read', tool_call_id='call_2')
    session.finalize_tool(
        idx,
        content=f'env contents:\n{FAKE_SK_ANT}',
    )
    stored = session.messages[-1].content
    assert FAKE_SK_ANT not in stored
    assert '[REDACTED:ant]' in stored


def test_streamed_delta_redacts_secret_straddling_chunk_boundary():
    session = AgentSessionState.create(system_prompt_parts=['sys'], user_prompt=None)
    idx = session.start_tool(name='Read', tool_call_id='call_3')
    # Split the fake token across two deltas. Per-delta redaction would miss
    # this; reassembled-content redaction catches it.
    half = len(FAKE_SK_ANT) // 2
    session.append_tool_delta(idx, FAKE_SK_ANT[:half])
    session.append_tool_delta(idx, FAKE_SK_ANT[half:])
    stored = session.messages[idx].content
    assert FAKE_SK_ANT not in stored
    assert '[REDACTED:ant]' in stored


def test_update_message_redacts_when_role_is_tool():
    """`update_message` is the post-hoc mutation path. If a caller routes
    tool output through it (e.g., to swap content after the fact), the
    secret must be redacted there too.
    """
    session = AgentSessionState.create(system_prompt_parts=['sys'], user_prompt=None)
    idx = session.start_tool(name='Read', tool_call_id='call_um')
    session.update_message(idx, content=f'API_KEY={FAKE_SK_ANT}')
    stored = session.messages[idx].content
    assert FAKE_SK_ANT not in stored
    assert '[REDACTED:ant]' in stored


def test_update_message_does_not_redact_assistant_content():
    """Redaction is scoped to tool-role messages. Assistant content is
    bounded by other walls (the model's own output). Don't widen scope
    silently — pin the boundary.
    """
    session = AgentSessionState.create(system_prompt_parts=['sys'], user_prompt=None)
    idx = session.start_assistant()
    session.update_message(idx, content=f'analyzing... {FAKE_SK_ANT}')
    assert FAKE_SK_ANT in session.messages[idx].content


def test_redact_stripe_underscore_token():
    fake_stripe = 'sk' + '_live_' + 'abcdefghijklmnopqrstuvwx'
    out = redact_secrets(f'STRIPE={fake_stripe}')
    assert fake_stripe not in out
    assert '[REDACTED:stripe]' in out


def test_redact_google_api_key():
    # Real Google API keys are 39 chars: `AIza` + 35 from [A-Za-z0-9_-].
    fake = 'AIza' + 'SyA1B2C3D4E5F6G7H8I9J0KaLbMcNdOePfQ'
    assert len(fake) == 39
    out = redact_secrets(f'GOOGLE_API_KEY={fake}')
    assert fake not in out
    assert '[REDACTED:google]' in out


def test_redact_jwt_triple_segment():
    jwt = (
        'eyJ' + 'hbGciOiJIUzI1NiJ9'
        + '.' + 'eyJ' + 'zdWIiOiIxMjM0NSIsIm5hbWUiOiJqIn0'
        + '.' + 'SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'
    )
    out = redact_secrets(f'token={jwt}')
    assert jwt not in out
    assert '[REDACTED:jwt]' in out


def test_jwt_pattern_does_not_false_positive_on_bare_eyJ():
    """`eyJ` alone is just base64 of `{"` and appears in unrelated content.
    The pattern requires three dot-separated segments; bare `eyJ` is fine.
    """
    out = redact_secrets('debug: parsing started with eyJ marker (not a token)')
    assert out == 'debug: parsing started with eyJ marker (not a token)'
