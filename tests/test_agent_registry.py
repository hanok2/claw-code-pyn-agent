from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.agent_registry import (
    create_agent_definition,
    delete_agent_definition,
    load_agent_registry,
    render_agent_detail,
    render_agents_report,
    update_agent_definition,
)


def _write_agent(path: Path, *, name: str, description: str, body: str, extra: str = '') -> None:
    payload = (
        '---\n'
        f'name: {name}\n'
        f'description: "{description}"\n'
        f'{extra}'
        '---\n\n'
        f'{body}\n'
    )
    path.write_text(payload, encoding='utf-8')


class AgentRegistryTests(unittest.TestCase):
    def test_create_update_delete_agent_definition_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as home_dir, tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            with patch.dict(os.environ, {'HOME': home_dir}):
                created = create_agent_definition(
                    workspace,
                    agent_type='reviewer',
                    description='Review implementation changes.',
                    system_prompt='Inspect diffs and summarize risks.',
                    source='project',
                    tools=('read_file', 'grep_search'),
                    model='demo-model',
                    initial_prompt='Start with changed files.',
                )
                self.assertEqual(created.action, 'created')
                self.assertTrue(Path(created.file_path).exists())

                snapshot = load_agent_registry(workspace)
                detail = render_agent_detail(snapshot, 'reviewer')
                self.assertIn('demo-model', detail)
                self.assertIn('Start with changed files.', detail)

                updated = update_agent_definition(
                    workspace,
                    agent_type='reviewer',
                    description='Review code and tests carefully.',
                    system_prompt='Focus on regressions and missing coverage.',
                    source='project',
                )
                self.assertEqual(updated.action, 'updated')

                snapshot = load_agent_registry(workspace)
                detail = render_agent_detail(snapshot, 'reviewer')
                self.assertIn('Review code and tests carefully.', detail)
                self.assertIn('Focus on regressions and missing coverage.', detail)

                deleted = delete_agent_definition(
                    workspace,
                    agent_type='reviewer',
                    source='project',
                )
                self.assertEqual(deleted.action, 'deleted')
                self.assertFalse(Path(deleted.file_path).exists())

    def test_project_agent_overrides_built_in_agent(self) -> None:
        with tempfile.TemporaryDirectory() as home_dir, tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            agents_dir = workspace / '.claude' / 'agents'
            agents_dir.mkdir(parents=True)
            _write_agent(
                agents_dir / 'Explore.md',
                name='Explore',
                description='Project-specific explore agent.',
                body='Search this repository carefully before answering.',
                extra=(
                    'tools: read_file, grep_search\n'
                    'model: child-model\n'
                    'initialPrompt: Begin with rg-style discovery.\n'
                ),
            )

            with patch.dict(os.environ, {'HOME': home_dir}):
                snapshot = load_agent_registry(workspace)

            active = {agent.agent_type: agent for agent in snapshot.active_agents}
            self.assertIn('Explore', active)
            self.assertEqual(active['Explore'].source, 'projectSettings')
            self.assertEqual(active['Explore'].model, 'child-model')
            self.assertEqual(active['Explore'].tools, ('read_file', 'grep_search'))
            self.assertEqual(active['Explore'].initial_prompt, 'Begin with rg-style discovery.')

            report = render_agents_report(snapshot, cwd=workspace)
            self.assertIn('Explore [projectSettings]', report)
            self.assertIn('Shadowed Agents', report)

            detail = render_agent_detail(snapshot, 'Explore')
            self.assertIn('Project-specific explore agent.', detail)
            self.assertIn('Begin with rg-style discovery.', detail)
            self.assertIn('Search this repository carefully before answering.', detail)

    def test_invalid_agent_file_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as home_dir, tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            agents_dir = workspace / '.claude' / 'agents'
            agents_dir.mkdir(parents=True)
            (agents_dir / 'broken.md').write_text(
                '---\nname: broken\n---\n',
                encoding='utf-8',
            )

            with patch.dict(os.environ, {'HOME': home_dir}):
                snapshot = load_agent_registry(workspace)

            self.assertEqual(len(snapshot.failed_files), 1)
            self.assertIn('missing a description', snapshot.failed_files[0].error)
