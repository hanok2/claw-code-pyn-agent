"""GUI entry point: ``python -m src.gui [--port N] [--cwd PATH] ...``."""

from __future__ import annotations

import argparse
import os
import webbrowser
from pathlib import Path

import uvicorn

from ..session_store import DEFAULT_AGENT_SESSION_DIR
from .server import AgentState, create_app


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='claw-code-gui',
        description='Launch the local web GUI for the claw-code agent.',
    )
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument(
        '--cwd',
        default='.',
        help='Working directory that the agent operates in (default: current dir).',
    )
    parser.add_argument(
        '--model',
        default=os.environ.get('OPENAI_MODEL', 'Qwen/Qwen3-Coder-30B-A3B-Instruct'),
    )
    parser.add_argument(
        '--base-url',
        default=os.environ.get('OPENAI_BASE_URL', 'http://127.0.0.1:8000/v1'),
    )
    parser.add_argument(
        '--api-key',
        default=os.environ.get('OPENAI_API_KEY', 'local-token'),
    )
    parser.add_argument(
        '--session-dir',
        default=str(DEFAULT_AGENT_SESSION_DIR),
        help='Directory where agent sessions are saved (default: .port_sessions/agent).',
    )
    parser.add_argument('--allow-shell', action='store_true')
    parser.add_argument('--allow-write', action='store_true')
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Do not auto-open a browser tab on launch.',
    )

    args = parser.parse_args()

    state = AgentState(
        cwd=Path(args.cwd),
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
        allow_shell=args.allow_shell,
        allow_write=args.allow_write,
        session_directory=Path(args.session_dir),
    )
    app = create_app(state)

    url = f'http://{args.host}:{args.port}'
    print(f'Claw Code GUI listening on {url}')
    print(f'  cwd       : {state.cwd}')
    print(f'  model     : {state.model}')
    print(f'  base-url  : {state.base_url}')
    print(f'  sessions  : {state.session_directory}')
    print(f'  shell     : {"on" if state.allow_shell else "off"}')
    print(f'  write     : {"on" if state.allow_write else "off"}')

    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    uvicorn.run(app, host=args.host, port=args.port, log_level='info')


if __name__ == '__main__':
    main()
