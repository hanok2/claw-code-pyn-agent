"""FastAPI server backing the local web GUI.

Wraps a single global :class:`LocalCodingAgent`, exposes JSON endpoints for
chat, slash commands, and saved sessions, and serves the static SPA.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..agent_runtime import LocalCodingAgent
from ..agent_slash_commands import get_slash_command_specs
from ..agent_types import (
    AgentPermissions,
    AgentRuntimeConfig,
    ModelConfig,
)
from ..bundled_skills import get_bundled_skills
from ..session_store import (
    DEFAULT_AGENT_SESSION_DIR,
    StoredAgentSession,
    load_agent_session,
)


STATIC_DIR = Path(__file__).parent / 'static'


# ---------------------------------------------------------------------------
# Agent state holder
# ---------------------------------------------------------------------------

class AgentState:
    """Holds the live agent instance plus a lock for serialized access."""

    def __init__(
        self,
        *,
        cwd: Path,
        model: str,
        base_url: str,
        api_key: str,
        allow_shell: bool,
        allow_write: bool,
        session_directory: Path,
    ) -> None:
        self.cwd = cwd.resolve()
        self.session_directory = session_directory
        self._lock = Lock()
        self._agent: LocalCodingAgent | None = None
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.allow_shell = allow_shell
        self.allow_write = allow_write
        self._build_agent()

    def _build_agent(self) -> None:
        permissions = AgentPermissions(
            allow_file_write=self.allow_write,
            allow_shell_commands=self.allow_shell,
        )
        runtime_config = AgentRuntimeConfig(
            cwd=self.cwd,
            permissions=permissions,
            session_directory=self.session_directory,
        )
        model_config = ModelConfig(
            model=self.model,
            base_url=self.base_url,
            api_key=self.api_key,
        )
        self._agent = LocalCodingAgent(
            model_config=model_config,
            runtime_config=runtime_config,
        )

    @property
    def agent(self) -> LocalCodingAgent:
        assert self._agent is not None
        return self._agent

    def update(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        cwd: str | None = None,
        allow_shell: bool | None = None,
        allow_write: bool | None = None,
    ) -> None:
        with self._lock:
            if model is not None:
                self.model = model
            if base_url is not None:
                self.base_url = base_url
            if api_key is not None:
                self.api_key = api_key
            if cwd is not None:
                resolved = Path(cwd).expanduser().resolve()
                if not resolved.is_dir():
                    raise ValueError(f'cwd does not exist: {resolved}')
                self.cwd = resolved
            if allow_shell is not None:
                self.allow_shell = allow_shell
            if allow_write is not None:
                self.allow_write = allow_write
            self._build_agent()

    def snapshot(self) -> dict[str, Any]:
        return {
            'model': self.model,
            'base_url': self.base_url,
            'cwd': str(self.cwd),
            'session_directory': str(self.session_directory),
            'allow_shell': self.allow_shell,
            'allow_write': self.allow_write,
            'active_session_id': self.agent.active_session_id,
        }

    def lock(self) -> Lock:
        return self._lock


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1)
    resume_session_id: str | None = None


class StateUpdate(BaseModel):
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    cwd: str | None = None
    allow_shell: bool | None = None
    allow_write: bool | None = None


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(state: AgentState) -> FastAPI:
    app = FastAPI(title='Claw Code GUI', version='1.0')

    # ------------- static + index ------------------------------------------
    app.mount(
        '/static',
        StaticFiles(directory=str(STATIC_DIR)),
        name='static',
    )

    @app.get('/', include_in_schema=False)
    async def root() -> FileResponse:
        return FileResponse(STATIC_DIR / 'index.html')

    # ------------- info ------------------------------------------------------
    @app.get('/api/state')
    async def get_state() -> dict[str, Any]:
        return state.snapshot()

    @app.post('/api/state')
    async def post_state(payload: StateUpdate) -> dict[str, Any]:
        try:
            state.update(**payload.model_dump(exclude_none=True))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return state.snapshot()

    @app.get('/api/slash-commands')
    async def list_slash_commands() -> list[dict[str, Any]]:
        commands: list[dict[str, Any]] = []
        for spec in get_slash_command_specs():
            commands.append(
                {
                    'names': list(spec.names),
                    'primary': spec.names[0],
                    'description': spec.description,
                }
            )
        return commands

    @app.get('/api/skills')
    async def list_skills() -> list[dict[str, Any]]:
        return [
            {
                'name': skill.name,
                'description': skill.description,
                'when_to_use': skill.when_to_use,
                'aliases': list(skill.aliases),
                'allowed_tools': list(skill.allowed_tools),
            }
            for skill in get_bundled_skills()
            if skill.user_invocable
        ]

    # ------------- sessions --------------------------------------------------
    @app.get('/api/sessions')
    async def list_sessions() -> list[dict[str, Any]]:
        directory = state.session_directory
        if not directory.exists():
            return []
        results: list[dict[str, Any]] = []
        for path in sorted(
            directory.glob('*.json'),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                continue
            messages = data.get('messages') or []
            preview = ''
            for msg in messages:
                if isinstance(msg, dict) and msg.get('role') == 'user':
                    content = msg.get('content', '')
                    if isinstance(content, str):
                        preview = content[:120]
                        break
            results.append(
                {
                    'session_id': data.get('session_id', path.stem),
                    'turns': data.get('turns', 0),
                    'tool_calls': data.get('tool_calls', 0),
                    'preview': preview,
                    'modified_at': path.stat().st_mtime,
                }
            )
        return results

    @app.get('/api/sessions/{session_id}')
    async def get_session(session_id: str) -> dict[str, Any]:
        try:
            stored = load_agent_session(session_id, directory=state.session_directory)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail='Session not found')
        return _serialize_stored_session(stored)

    # ------------- chat ------------------------------------------------------
    @app.post('/api/chat')
    async def chat(request: ChatRequest) -> dict[str, Any]:
        prompt = request.prompt.strip()
        if not prompt:
            raise HTTPException(status_code=400, detail='Prompt is empty')

        def _run() -> dict[str, Any]:
            with state.lock():
                agent = state.agent
                if request.resume_session_id is not None:
                    try:
                        stored = load_agent_session(
                            request.resume_session_id,
                            directory=state.session_directory,
                        )
                    except FileNotFoundError:
                        raise HTTPException(
                            status_code=404,
                            detail='Session to resume not found',
                        )
                    result = agent.resume(prompt, stored)
                else:
                    result = agent.run(prompt)
                return _serialize_run_result(result)

        try:
            payload = await asyncio.to_thread(_run)
        except HTTPException:
            raise
        except Exception as exc:  # surface the error in the UI
            return JSONResponse(
                status_code=500,
                content={
                    'error': str(exc),
                    'error_type': type(exc).__name__,
                },
            )
        return payload

    @app.post('/api/clear')
    async def clear_state() -> dict[str, Any]:
        with state.lock():
            state.agent.clear_runtime_state()
        return state.snapshot()

    return app


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _serialize_run_result(result: Any) -> dict[str, Any]:
    return {
        'final_output': result.final_output,
        'turns': result.turns,
        'tool_calls': result.tool_calls,
        'transcript': [_normalize_transcript_entry(entry) for entry in result.transcript],
        'session_id': result.session_id,
        'usage': result.usage.to_dict(),
        'total_cost_usd': result.total_cost_usd,
        'stop_reason': result.stop_reason,
    }


def _normalize_transcript_entry(entry: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        'role': entry.get('role', ''),
        'content': entry.get('content', ''),
    }
    for key in ('name', 'tool_call_id', 'tool_calls', 'metadata', 'message_id'):
        if key in entry and entry[key] not in (None, '', [], {}):
            out[key] = entry[key]
    return out


def _serialize_stored_session(stored: StoredAgentSession) -> dict[str, Any]:
    return {
        'session_id': stored.session_id,
        'turns': stored.turns,
        'tool_calls': stored.tool_calls,
        'messages': [_normalize_transcript_entry(dict(m)) for m in stored.messages],
        'usage': stored.usage,
        'total_cost_usd': stored.total_cost_usd,
        'model': stored.model_config.get('model'),
    }
