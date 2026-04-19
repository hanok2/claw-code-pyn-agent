from __future__ import annotations

import tempfile
import unittest
import json
import sys
import os
from pathlib import Path
from unittest.mock import patch

from src.agent_runtime import LocalCodingAgent
from src.agent_slash_commands import looks_like_command, parse_slash_command
from src.agent_types import AgentRuntimeConfig, ModelConfig
from src.plan_runtime import PlanRuntime
from src.task_runtime import TaskRuntime


class _FakeHTTPResponse:
    def __init__(self, payload: str) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return self.payload.encode('utf-8')

    def __enter__(self) -> '_FakeHTTPResponse':
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def _write_fake_mcp_server(workspace: Path) -> Path:
    server_path = workspace / 'fake_mcp_server.py'
    server_path.write_text(
        (
            'import json, sys\n'
            'TOOLS = [{"name": "echo", "description": "Echo text", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}}}]\n'
            'for raw in sys.stdin:\n'
            '    raw = raw.strip()\n'
            '    if not raw:\n'
            '        continue\n'
            '    message = json.loads(raw)\n'
            '    method = message.get("method")\n'
            '    if method == "initialize":\n'
            '        response = {"jsonrpc": "2.0", "id": message.get("id"), "result": {"protocolVersion": "2025-11-25", "capabilities": {"resources": {}, "tools": {}}, "serverInfo": {"name": "fake-remote", "version": "1.0.0"}}}\n'
            '        print(json.dumps(response), flush=True)\n'
            '        continue\n'
            '    if method == "notifications/initialized":\n'
            '        continue\n'
            '    if method == "tools/list":\n'
            '        response = {"jsonrpc": "2.0", "id": message.get("id"), "result": {"tools": TOOLS}}\n'
            '        print(json.dumps(response), flush=True)\n'
            '        continue\n'
            '    if method == "tools/call":\n'
            '        text = message.get("params", {}).get("arguments", {}).get("text", "")\n'
            '        response = {"jsonrpc": "2.0", "id": message.get("id"), "result": {"content": [{"type": "text", "text": "echo:" + text}], "isError": False}}\n'
            '        print(json.dumps(response), flush=True)\n'
            '        continue\n'
            '    response = {"jsonrpc": "2.0", "id": message.get("id"), "result": {"resources": []}}\n'
            '    print(json.dumps(response), flush=True)\n'
        ),
        encoding='utf-8',
    )
    return server_path


class AgentSlashCommandTests(unittest.TestCase):
    def test_parse_slash_command(self) -> None:
        parsed = parse_slash_command('/context extra args')
        assert parsed is not None
        self.assertEqual(parsed.command_name, 'context')
        self.assertEqual(parsed.args, 'extra args')
        self.assertFalse(parsed.is_mcp)

    def test_looks_like_command(self) -> None:
        self.assertTrue(looks_like_command('context'))
        self.assertFalse(looks_like_command('foo/bar'))

    def test_model_command_updates_agent_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            agent = LocalCodingAgent(
                model_config=ModelConfig(model='Qwen/Qwen3-Coder-30B-A3B-Instruct'),
                runtime_config=AgentRuntimeConfig(cwd=Path(tmp_dir)),
            )
            result = agent.run('/model local/test-model')
        self.assertIn('Set model to local/test-model', result.final_output)
        self.assertEqual(agent.model_config.model, 'local/test-model')

    def test_unknown_command_returns_local_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            agent = LocalCodingAgent(
                model_config=ModelConfig(model='Qwen/Qwen3-Coder-30B-A3B-Instruct'),
                runtime_config=AgentRuntimeConfig(cwd=Path(tmp_dir)),
            )
            result = agent.run('/unknown-command')
        self.assertEqual(result.final_output, 'Unknown skill: unknown-command')

    def test_context_command_renders_usage_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            (workspace / 'CLAUDE.md').write_text('repo instructions\n', encoding='utf-8')
            agent = LocalCodingAgent(
                model_config=ModelConfig(model='test-model'),
                runtime_config=AgentRuntimeConfig(cwd=workspace),
            )
            result = agent.run('/context')
        self.assertIn('## Context Usage', result.final_output)
        self.assertIn('### Estimated usage by category', result.final_output)
        self.assertIn('### Memory Files', result.final_output)

    def test_token_budget_command_renders_local_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            agent = LocalCodingAgent(
                model_config=ModelConfig(model='test-model'),
                runtime_config=AgentRuntimeConfig(cwd=workspace),
            )
            result = agent.run('/token-budget')
        self.assertIn('# Token Budget', result.final_output)
        self.assertIn('Hard input limit', result.final_output)
        self.assertIn('Auto-compact buffer', result.final_output)

    def test_agents_command_lists_and_shows_custom_agents(self) -> None:
        with tempfile.TemporaryDirectory() as home_dir, tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            agents_dir = workspace / '.claude' / 'agents'
            agents_dir.mkdir(parents=True)
            (agents_dir / 'reviewer.md').write_text(
                (
                    '---\n'
                    'name: reviewer\n'
                    'description: "Review implementation changes carefully."\n'
                    'tools: read_file, grep_search\n'
                    'model: test-child-model\n'
                    '---\n\n'
                    'Inspect code changes and summarize risks.\n'
                ),
                encoding='utf-8',
            )
            with patch.dict(os.environ, {'HOME': home_dir}):
                agent = LocalCodingAgent(
                    model_config=ModelConfig(model='test-model'),
                    runtime_config=AgentRuntimeConfig(cwd=workspace),
                )
                list_result = agent.run('/agents')
                detail_result = agent.run('/agents show reviewer')
        self.assertIn('# Agents', list_result.final_output)
        self.assertIn('reviewer [projectSettings]', list_result.final_output)
        self.assertIn('# Agent: reviewer', detail_result.final_output)
        self.assertIn('Inspect code changes and summarize risks.', detail_result.final_output)

    def test_agents_command_can_create_update_and_delete_project_agent(self) -> None:
        with tempfile.TemporaryDirectory() as home_dir, tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            with patch.dict(os.environ, {'HOME': home_dir}):
                agent = LocalCodingAgent(
                    model_config=ModelConfig(model='test-model'),
                    runtime_config=AgentRuntimeConfig(cwd=workspace),
                )
                create_result = agent.run(
                    '/agents create reviewer :: Review code changes carefully. :: Inspect code changes and summarize risks.'
                )
                self.assertIn('action=created', create_result.final_output)
                self.assertTrue((workspace / '.claude' / 'agents' / 'reviewer.md').exists())

                update_result = agent.run(
                    '/agents update reviewer Updated review description :: Focus on regressions and missing tests.'
                )
                self.assertIn('action=updated', update_result.final_output)

                detail_result = agent.run('/agents reviewer')
                self.assertIn('Updated review description', detail_result.final_output)
                self.assertIn('Focus on regressions and missing tests.', detail_result.final_output)

                delete_result = agent.run('/agents delete reviewer')
                self.assertIn('action=deleted', delete_result.final_output)
                self.assertFalse((workspace / '.claude' / 'agents' / 'reviewer.md').exists())

    def test_mcp_and_resource_commands_render_local_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            (workspace / 'notes.txt').write_text('mcp notes\n', encoding='utf-8')
            (workspace / '.claw-mcp.json').write_text(
                (
                    '{"servers":[{"name":"workspace","resources":['
                    '{"uri":"mcp://workspace/notes","name":"Notes","path":"notes.txt"}'
                    ']}]}'
                ),
                encoding='utf-8',
            )
            agent = LocalCodingAgent(
                model_config=ModelConfig(model='Qwen/Qwen3-Coder-30B-A3B-Instruct'),
                runtime_config=AgentRuntimeConfig(cwd=workspace),
            )
            mcp_result = agent.run('/mcp')
            resources_result = agent.run('/resources')
            resource_result = agent.run('/resource mcp://workspace/notes')
            legacy_mcp_result = agent.run('/mcp (MCP)')
        self.assertIn('# MCP', mcp_result.final_output)
        self.assertIn('Local MCP resources: 1', mcp_result.final_output)
        self.assertIn('# MCP Resources', resources_result.final_output)
        self.assertIn('mcp://workspace/notes', resources_result.final_output)
        self.assertIn('# MCP Resource', resource_result.final_output)
        self.assertIn('mcp notes', resource_result.final_output)
        self.assertIn('# MCP', legacy_mcp_result.final_output)

    def test_mcp_tools_command_renders_transport_backed_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            server_path = _write_fake_mcp_server(workspace)
            (workspace / '.claw-mcp.json').write_text(
                json.dumps(
                    {
                        'mcpServers': {
                            'remote': {
                                'command': sys.executable,
                                'args': ['-u', str(server_path)],
                            }
                        }
                    }
                ),
                encoding='utf-8',
            )
            agent = LocalCodingAgent(
                model_config=ModelConfig(model='Qwen/Qwen3-Coder-30B-A3B-Instruct'),
                runtime_config=AgentRuntimeConfig(cwd=workspace),
            )
            tools_result = agent.run('/mcp tools')
            tool_result = agent.run('/mcp tool echo')
        self.assertIn('# MCP Tools', tools_result.final_output)
        self.assertIn('echo', tools_result.final_output)
        self.assertIn('# MCP Tool Result', tool_result.final_output)
        self.assertIn('echo:', tool_result.final_output)

    def test_search_commands_render_and_update_local_search_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            (workspace / '.claw-search.json').write_text(
                (
                    '{"providers":['
                    '{"name":"local-search","provider":"searxng","baseUrl":"http://127.0.0.1:8080"},'
                    '{"name":"backup-search","provider":"searxng","baseUrl":"http://127.0.0.2:8080"}'
                    ']}'
                ),
                encoding='utf-8',
            )
            agent = LocalCodingAgent(
                model_config=ModelConfig(model='Qwen/Qwen3-Coder-30B-A3B-Instruct'),
                runtime_config=AgentRuntimeConfig(cwd=workspace),
            )
            with patch(
                'src.search_runtime.request.urlopen',
                return_value=_FakeHTTPResponse(
                    '{"results":[{"title":"Alpha","url":"https://example.com/alpha","content":"Search snippet"}]}'
                ),
            ):
                search_result = agent.run('/search alpha query')
            providers_result = agent.run('/search providers')
            activate_result = agent.run('/search use backup-search')
            provider_result = agent.run('/search provider backup-search')
        self.assertIn('# Web Search', search_result.final_output)
        self.assertIn('Alpha', search_result.final_output)
        self.assertIn('# Search Providers', providers_result.final_output)
        self.assertIn('local-search', providers_result.final_output)
        self.assertIn('backup-search', providers_result.final_output)
        self.assertIn('provider=backup-search', activate_result.final_output)
        self.assertIn('# Search Provider', provider_result.final_output)
        self.assertIn('backup-search', provider_result.final_output)

    def test_lsp_commands_render_local_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            (workspace / 'sample.py').write_text(
                'def helper(value):\n'
                '    """Double a value."""\n'
                '    return value * 2\n'
                '\n'
                'def run(item):\n'
                '    return helper(item)\n',
                encoding='utf-8',
            )
            agent = LocalCodingAgent(
                model_config=ModelConfig(model='Qwen/Qwen3-Coder-30B-A3B-Instruct'),
                runtime_config=AgentRuntimeConfig(cwd=workspace),
            )
            summary_result = agent.run('/lsp')
            symbols_result = agent.run('/lsp symbols sample.py')
            definition_result = agent.run('/lsp definition sample.py 6 12')
            diagnostics_result = agent.run('/lsp diagnostics sample.py')
        self.assertIn('# LSP', summary_result.final_output)
        self.assertIn('Indexed candidate files: 1', summary_result.final_output)
        self.assertIn('# LSP Document Symbols', symbols_result.final_output)
        self.assertIn('function helper', symbols_result.final_output)
        self.assertIn('# LSP Definition', definition_result.final_output)
        self.assertIn('function helper', definition_result.final_output)
        self.assertIn('# LSP Diagnostics', diagnostics_result.final_output)

    def test_remote_commands_render_and_update_local_remote_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            (workspace / '.claw-remote.json').write_text(
                (
                    '{"profiles":[{"name":"staging","mode":"ssh","target":"dev@staging",'
                    '"workspaceCwd":"/srv/app","sessionUrl":"wss://remote/session"}]}'
                ),
                encoding='utf-8',
            )
            agent = LocalCodingAgent(
                model_config=ModelConfig(model='Qwen/Qwen3-Coder-30B-A3B-Instruct'),
                runtime_config=AgentRuntimeConfig(cwd=workspace),
            )
            remotes_result = agent.run('/remotes')
            remote_result = agent.run('/remote')
            ssh_result = agent.run('/ssh staging')
            disconnect_result = agent.run('/disconnect')
        self.assertIn('# Remote Profiles', remotes_result.final_output)
        self.assertIn('staging', remotes_result.final_output)
        self.assertIn('# Remote', remote_result.final_output)
        self.assertIn('Configured remote profiles: 1', remote_result.final_output)
        self.assertIn('mode=ssh', ssh_result.final_output)
        self.assertIn('profile=staging', ssh_result.final_output)
        self.assertIn('connected=False', disconnect_result.final_output)

    def test_workflow_and_trigger_commands_render_local_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            (workspace / '.claw-workflows.json').write_text(
                (
                    '{"workflows":['
                    '{"name":"review","description":"Review changes.","steps":["Inspect diff","Summarize findings"]}'
                    ']}'
                ),
                encoding='utf-8',
            )
            (workspace / '.claw-triggers.json').write_text(
                (
                    '{"triggers":['
                    '{"trigger_id":"nightly","name":"Nightly","workflow":"review","schedule":"0 0 * * *"}'
                    ']}'
                ),
                encoding='utf-8',
            )
            agent = LocalCodingAgent(
                model_config=ModelConfig(model='Qwen/Qwen3-Coder-30B-A3B-Instruct'),
                runtime_config=AgentRuntimeConfig(cwd=workspace),
            )
            workflows_result = agent.run('/workflows')
            workflow_result = agent.run('/workflow review')
            trigger_result = agent.run('/trigger nightly')
            trigger_run_result = agent.run('/trigger run nightly')
        self.assertIn('# Workflows', workflows_result.final_output)
        self.assertIn('review', workflows_result.final_output)
        self.assertIn('# Workflow', workflow_result.final_output)
        self.assertIn('Review changes', workflow_result.final_output)
        self.assertIn('# Remote Trigger', trigger_result.final_output)
        self.assertIn('trigger_id=nightly', trigger_result.final_output)
        self.assertIn('# Remote Trigger Run', trigger_run_result.final_output)

    def test_account_commands_render_and_update_local_account_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            (workspace / '.claw-account.json').write_text(
                '{"profiles":[{"name":"local","provider":"openai","identity":"dev@example.com"}]}',
                encoding='utf-8',
            )
            agent = LocalCodingAgent(
                model_config=ModelConfig(model='Qwen/Qwen3-Coder-30B-A3B-Instruct'),
                runtime_config=AgentRuntimeConfig(cwd=workspace),
            )
            account_result = agent.run('/account')
            profiles_result = agent.run('/account profiles')
            login_result = agent.run('/login local')
            logout_result = agent.run('/logout')
        self.assertIn('# Account', account_result.final_output)
        self.assertIn('Configured account profiles: 1', account_result.final_output)
        self.assertIn('# Account Profiles', profiles_result.final_output)
        self.assertIn('dev@example.com', profiles_result.final_output)
        self.assertIn('profile=local', login_result.final_output)
        self.assertIn('logged_in=False', logout_result.final_output)

    def test_ask_commands_render_local_ask_user_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            (workspace / '.claw-ask-user.json').write_text(
                '{"answers":[{"question":"Approve deploy?","answer":"yes"}]}',
                encoding='utf-8',
            )
            agent = LocalCodingAgent(
                model_config=ModelConfig(model='Qwen/Qwen3-Coder-30B-A3B-Instruct'),
                runtime_config=AgentRuntimeConfig(cwd=workspace),
            )
            status_result = agent.run('/ask')
            history_result = agent.run('/ask history')
        self.assertIn('# Ask User', status_result.final_output)
        self.assertIn('Queued answers: 1', status_result.final_output)
        self.assertIn('# Ask User History', history_result.final_output)

    def test_team_commands_render_local_team_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            (workspace / '.claw-teams.json').write_text(
                '{"teams":[{"name":"reviewers","members":["alice","bob"]}]}',
                encoding='utf-8',
            )
            agent = LocalCodingAgent(
                model_config=ModelConfig(model='Qwen/Qwen3-Coder-30B-A3B-Instruct'),
                runtime_config=AgentRuntimeConfig(cwd=workspace),
            )
            teams_result = agent.run('/teams')
            team_result = agent.run('/team reviewers')
            messages_result = agent.run('/messages')
        self.assertIn('# Teams', teams_result.final_output)
        self.assertIn('reviewers', teams_result.final_output)
        self.assertIn('# Team', team_result.final_output)
        self.assertIn('alice', team_result.final_output)
        self.assertIn('# Team Messages', messages_result.final_output)

    def test_config_commands_render_local_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            claude_dir = workspace / '.claude'
            claude_dir.mkdir()
            (claude_dir / 'settings.json').write_text(
                '{"review":{"mode":"strict"}}',
                encoding='utf-8',
            )
            agent = LocalCodingAgent(
                model_config=ModelConfig(model='Qwen/Qwen3-Coder-30B-A3B-Instruct'),
                runtime_config=AgentRuntimeConfig(cwd=workspace),
            )
            config_result = agent.run('/config')
            effective_result = agent.run('/config effective')
            value_result = agent.run('/config get review.mode')
            source_result = agent.run('/settings source project')
        self.assertIn('# Config', config_result.final_output)
        self.assertIn('Config sources: 1', config_result.final_output)
        self.assertIn('# Config Effective', effective_result.final_output)
        self.assertIn('"review"', effective_result.final_output)
        self.assertIn('# Config Value', value_result.final_output)
        self.assertIn('"strict"', value_result.final_output)
        self.assertIn('# Config Source', source_result.final_output)

    def test_tasks_and_task_commands_render_local_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            runtime = TaskRuntime.from_workspace(workspace)
            mutation = runtime.create_task(
                title='Review runtime tasks',
                status='in_progress',
            )
            task_id = mutation.task.task_id if mutation.task is not None else ''
            agent = LocalCodingAgent(
                model_config=ModelConfig(model='Qwen/Qwen3-Coder-30B-A3B-Instruct'),
                runtime_config=AgentRuntimeConfig(cwd=workspace),
            )
            tasks_result = agent.run('/tasks')
            task_result = agent.run(f'/task {task_id}')
            todo_result = agent.run('/todo in_progress')
            next_result = agent.run('/task-next')
        self.assertIn('# Tasks', tasks_result.final_output)
        self.assertIn(task_id, tasks_result.final_output)
        self.assertIn('# Task', task_result.final_output)
        self.assertIn('in_progress', task_result.final_output)
        self.assertIn('# Tasks', todo_result.final_output)
        self.assertIn('# Next Tasks', next_result.final_output)
        self.assertIn(task_id, next_result.final_output)

    def test_plan_command_renders_local_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            plan_runtime = PlanRuntime.from_workspace(workspace)
            plan_runtime.update_plan(
                [{'step': 'Inspect the plan command', 'status': 'in_progress'}],
                explanation='Use the local plan runtime.',
            )
            agent = LocalCodingAgent(
                model_config=ModelConfig(model='Qwen/Qwen3-Coder-30B-A3B-Instruct'),
                runtime_config=AgentRuntimeConfig(cwd=workspace),
            )
            plan_result = agent.run('/plan')
        self.assertIn('# Plan', plan_result.final_output)
        self.assertIn('Inspect the plan command', plan_result.final_output)

    def test_tools_and_status_commands_render_local_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            agent = LocalCodingAgent(
                model_config=ModelConfig(model='test-model'),
                runtime_config=AgentRuntimeConfig(cwd=Path(tmp_dir)),
            )
            tools_result = agent.run('/tools')
            status_result = agent.run('/status')
        self.assertIn('# Tools', tools_result.final_output)
        self.assertIn('`read_file`', tools_result.final_output)
        self.assertIn('# Status', status_result.final_output)
        self.assertIn('Token counter:', status_result.final_output)
        self.assertIn('Last run: none', status_result.final_output)

    def test_hooks_and_trust_commands_render_local_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            (workspace / '.claw-policy.json').write_text(
                (
                    '{"trusted": false, '
                    '"managedSettings": {"reviewMode": "strict"}, '
                    '"safeEnv": ["HOOK_SAFE_TOKEN"]}'
                ),
                encoding='utf-8',
            )
            with patch.dict('os.environ', {'HOOK_SAFE_TOKEN': 'demo-secret'}, clear=False):
                agent = LocalCodingAgent(
                    model_config=ModelConfig(model='Qwen/Qwen3-Coder-30B-A3B-Instruct'),
                    runtime_config=AgentRuntimeConfig(cwd=workspace),
                )
                hooks_result = agent.run('/hooks')
                trust_result = agent.run('/trust')
        self.assertIn('# Hook Policy', hooks_result.final_output)
        self.assertIn('Local hook/policy manifests', hooks_result.final_output)
        self.assertIn('# Trust', trust_result.final_output)
        self.assertIn('untrusted', trust_result.final_output)
        self.assertIn('reviewMode=strict', trust_result.final_output)
        self.assertIn('HOOK_SAFE_TOKEN=demo-secret', trust_result.final_output)

    def test_clear_command_clears_saved_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            agent = LocalCodingAgent(
                model_config=ModelConfig(model='Qwen/Qwen3-Coder-30B-A3B-Instruct'),
                runtime_config=AgentRuntimeConfig(cwd=Path(tmp_dir)),
            )
            agent.last_session = agent.build_session('hello')
            agent.last_run_result = object()  # type: ignore[assignment]
            result = agent.run('/clear')
        self.assertIn('Cleared ephemeral Python agent state', result.final_output)
        self.assertIsNone(agent.last_session)
        self.assertIsNone(agent.last_run_result)
