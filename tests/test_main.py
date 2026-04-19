from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from src.main import _build_runtime_config, _build_agent, _run_agent_chat_loop, build_parser, main


class FakeHTTPResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode('utf-8')

    def __enter__(self) -> 'FakeHTTPResponse':
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def make_urlopen_side_effect(responses: list[dict[str, object]]):
    queued = [FakeHTTPResponse(payload) for payload in responses]

    def _fake_urlopen(request_obj, timeout=None):  # noqa: ANN001
        return queued.pop(0)

    return _fake_urlopen


class MainCliTests(unittest.TestCase):
    def test_build_runtime_config_parses_model_and_session_budget_flags(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                'agent',
                'Summarize the repo',
                '--cwd',
                '.',
                '--max-model-calls',
                '3',
                '--max-session-turns',
                '5',
            ]
        )
        runtime_config = _build_runtime_config(args)
        self.assertEqual(runtime_config.budget_config.max_model_calls, 3)
        self.assertEqual(runtime_config.budget_config.max_session_turns, 5)

    def test_agent_chat_loop_runs_multiple_turns_and_reuses_session(self) -> None:
        responses = [
            {
                'choices': [
                    {
                        'message': {
                            'role': 'assistant',
                            'content': 'First chat reply.',
                        },
                        'finish_reason': 'stop',
                    }
                ],
                'usage': {'prompt_tokens': 5, 'completion_tokens': 2},
            },
            {
                'choices': [
                    {
                        'message': {
                            'role': 'assistant',
                            'content': 'Second chat reply.',
                        },
                        'finish_reason': 'stop',
                    }
                ],
                'usage': {'prompt_tokens': 6, 'completion_tokens': 2},
            },
        ]
        recorded_results: list[str] = []
        recorded_lines: list[str] = []
        prompts = iter(['Second prompt', '/exit'])

        def _input(prompt: str) -> str:
            return next(prompts)

        def _output(line: str) -> None:
            recorded_lines.append(line)

        def _result_printer(result, *, show_transcript: bool) -> None:  # noqa: ANN001
            recorded_results.append(result.final_output)

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            session_dir = workspace / '.port_sessions' / 'agent'
            with patch(
                'src.openai_compat.request.urlopen',
                side_effect=make_urlopen_side_effect(responses),
            ):
                parser = build_parser()
                args = parser.parse_args(
                    [
                        'agent-chat',
                        'First prompt',
                        '--model',
                        'test-model',
                        '--cwd',
                        str(workspace),
                    ]
                )
                agent = _build_agent(args)
                agent.runtime_config = replace(
                    agent.runtime_config,
                    session_directory=session_dir,
                )
                exit_code = _run_agent_chat_loop(
                    agent,
                    initial_prompt=args.prompt,
                    resume_session_id=None,
                    show_transcript=False,
                    input_func=_input,
                    output_func=_output,
                    result_printer=_result_printer,
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(recorded_results, ['First chat reply.', 'Second chat reply.'])
        self.assertIn('# Agent Chat', recorded_lines)
        self.assertIn('chat_ended=user_exit', recorded_lines)

    def test_parser_accepts_remote_runtime_commands(self) -> None:
        parser = build_parser()
        args = parser.parse_args(['remote-profiles', '--cwd', '.'])
        self.assertEqual(args.command, 'remote-profiles')
        self.assertEqual(args.cwd, '.')

    def test_parser_accepts_account_runtime_commands(self) -> None:
        parser = build_parser()
        args = parser.parse_args(['account-profiles', '--cwd', '.'])
        self.assertEqual(args.command, 'account-profiles')
        self.assertEqual(args.cwd, '.')

    def test_parser_accepts_ask_user_runtime_commands(self) -> None:
        parser = build_parser()
        args = parser.parse_args(['ask-history', '--cwd', '.'])
        self.assertEqual(args.command, 'ask-history')
        self.assertEqual(args.cwd, '.')

    def test_parser_accepts_search_runtime_commands(self) -> None:
        parser = build_parser()
        args = parser.parse_args(['search', 'repo query', '--cwd', '.', '--provider', 'local-search'])
        self.assertEqual(args.command, 'search')
        self.assertEqual(args.query, 'repo query')
        self.assertEqual(args.provider, 'local-search')
        self.assertEqual(args.cwd, '.')

    def test_parser_accepts_worktree_runtime_commands(self) -> None:
        parser = build_parser()
        args = parser.parse_args(['worktree-exit', '--action', 'remove', '--discard-changes', '--cwd', '.'])
        self.assertEqual(args.command, 'worktree-exit')
        self.assertEqual(args.action, 'remove')
        self.assertTrue(args.discard_changes)
        self.assertEqual(args.cwd, '.')

    def test_parser_accepts_workflow_runtime_commands(self) -> None:
        parser = build_parser()
        args = parser.parse_args(['workflow-run', 'review', '--arguments-json', '{"path":"src"}', '--cwd', '.'])
        self.assertEqual(args.command, 'workflow-run')
        self.assertEqual(args.workflow_name, 'review')
        self.assertEqual(args.cwd, '.')

    def test_parser_accepts_remote_trigger_runtime_commands(self) -> None:
        parser = build_parser()
        args = parser.parse_args(['trigger-run', 'nightly', '--body-json', '{"depth":"quick"}', '--cwd', '.'])
        self.assertEqual(args.command, 'trigger-run')
        self.assertEqual(args.trigger_id, 'nightly')
        self.assertEqual(args.cwd, '.')

    def test_parser_accepts_mcp_runtime_commands(self) -> None:
        parser = build_parser()
        args = parser.parse_args(['mcp-tools', '--cwd', '.', '--server', 'remote'])
        self.assertEqual(args.command, 'mcp-tools')
        self.assertEqual(args.server, 'remote')
        self.assertEqual(args.cwd, '.')

    def test_parser_accepts_daemon_subcommands(self) -> None:
        parser = build_parser()
        args = parser.parse_args(['daemon', 'ps'])
        self.assertEqual(args.command, 'daemon')
        self.assertEqual(args.daemon_command, 'ps')

    def test_parser_accepts_config_runtime_commands(self) -> None:
        parser = build_parser()
        args = parser.parse_args(['config-get', 'review.mode', '--cwd', '.'])
        self.assertEqual(args.command, 'config-get')
        self.assertEqual(args.key_path, 'review.mode')
        self.assertEqual(args.cwd, '.')

    def test_parser_accepts_lsp_runtime_commands(self) -> None:
        parser = build_parser()
        args = parser.parse_args(['lsp-definition', 'sample.py', '4', '12', '--cwd', '.'])
        self.assertEqual(args.command, 'lsp-definition')
        self.assertEqual(args.file_path, 'sample.py')
        self.assertEqual(args.line, 4)
        self.assertEqual(args.character, 12)
        self.assertEqual(args.cwd, '.')

    def test_parser_accepts_token_budget_command(self) -> None:
        parser = build_parser()
        args = parser.parse_args(['token-budget', '--cwd', '.'])
        self.assertEqual(args.command, 'token-budget')
        self.assertEqual(args.cwd, '.')

    def test_parser_accepts_agents_command(self) -> None:
        parser = build_parser()
        args = parser.parse_args(['agents', 'reviewer', '--cwd', '.', '--all'])
        self.assertEqual(args.command, 'agents')
        self.assertEqual(args.agent_type, 'reviewer')
        self.assertTrue(args.all)
        self.assertEqual(args.cwd, '.')

    def test_parser_accepts_agent_management_commands(self) -> None:
        parser = build_parser()
        create_args = parser.parse_args(
            ['agents-create', 'reviewer', '--cwd', '.', '--description', 'Review code', '--prompt', 'Inspect diffs']
        )
        self.assertEqual(create_args.command, 'agents-create')
        self.assertEqual(create_args.agent_type, 'reviewer')
        self.assertEqual(create_args.description, 'Review code')

        update_args = parser.parse_args(['agents-update', 'reviewer', '--cwd', '.', '--source', 'auto'])
        self.assertEqual(update_args.command, 'agents-update')
        self.assertEqual(update_args.source, 'auto')

        delete_args = parser.parse_args(['agents-delete', 'reviewer', '--cwd', '.', '--source', 'project'])
        self.assertEqual(delete_args.command, 'agents-delete')
        self.assertEqual(delete_args.source, 'project')

    def test_main_can_create_and_delete_agent_definition(self) -> None:
        with tempfile.TemporaryDirectory() as home_dir, tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            with patch.dict('os.environ', {'HOME': home_dir}):
                exit_code = main(
                    [
                        'agents-create',
                        'reviewer',
                        '--cwd',
                        str(workspace),
                        '--description',
                        'Review code carefully',
                        '--prompt',
                        'Inspect code and summarize risks.',
                    ]
                )
                self.assertEqual(exit_code, 0)
                self.assertTrue((workspace / '.claude' / 'agents' / 'reviewer.md').exists())

                exit_code = main(
                    [
                        'agents-delete',
                        'reviewer',
                        '--cwd',
                        str(workspace),
                        '--source',
                        'project',
                    ]
                )
                self.assertEqual(exit_code, 0)
                self.assertFalse((workspace / '.claude' / 'agents' / 'reviewer.md').exists())

    def test_parser_accepts_team_runtime_commands(self) -> None:
        parser = build_parser()
        args = parser.parse_args(['team-create', 'reviewers', '--member', 'alice', '--cwd', '.'])
        self.assertEqual(args.command, 'team-create')
        self.assertEqual(args.team_name, 'reviewers')
        self.assertEqual(args.member, ['alice'])
        self.assertEqual(args.cwd, '.')
