<p align="center">
  <img src="images/logo.png" alt="Claw Code Agent logo" width="420" />
</p>

<h1 align="center">Claw Code Agent</h1>

<p align="center">
  <em>A Python reimplementation of the Claude Code agent architecture — local models, full control, zero dependencies.</em>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="https://github.com/HarnessLab/claw-code-agent"><img src="https://img.shields.io/badge/repo-HarnessLab%2Fclaw--code--agent-181717?logo=github" alt="GitHub"></a>
  <a href="https://docs.vllm.ai/"><img src="https://img.shields.io/badge/backend-vLLM-FF6F00?logo=lightning&logoColor=white" alt="vLLM"></a>
  <a href="https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct"><img src="https://img.shields.io/badge/model-Qwen3--Coder-FFD21E?logo=huggingface&logoColor=black" alt="Qwen3-Coder"></a>
  <img src="https://img.shields.io/badge/dependencies-zero-brightgreen" alt="Zero Dependencies">
  <img src="https://img.shields.io/badge/status-alpha-orange" alt="Alpha">
  <img src="https://img.shields.io/badge/license-open--source-green" alt="License">
</p>

---

## 📢 What's New

> **April 2026 — Major Update**

| | Feature | Details |
|---|---------|---------|
| 🆕 | **Interactive Chat Mode** | New `agent-chat` command — multi-turn REPL with `/exit` to quit |
| 🆕 | **Streaming Output** | Token-by-token streaming with `--stream` flag |
| 🆕 | **Plugin Runtime** | Full manifest-based plugin system — hooks, tool aliases, virtual tools, tool blocking |
| 🆕 | **Nested Agent Delegation** | Delegate subtasks to child agents with dependency-aware topological batching |
| 🆕 | **Agent Manager** | Lineage tracking, group membership, batch summaries for nested agents |
| 🆕 | **Custom Agent Profiles** | Discover local markdown-defined agents from `~/.claude/agents` and `./.claude/agents` and use them through the `Agent` tool |
| 🆕 | **Cost Tracking & Budgets** | Token budgets, cost budgets, tool-call limits, model-call limits, session-turn limits |
| 🆕 | **Structured Output** | JSON schema response mode with `--response-schema-file` |
| 🆕 | **Context Compaction** | Auto-snip, auto-compact, and reactive compaction on prompt-too-long errors |
| 🆕 | **File History Replay** | Journaling of file edits with snapshot IDs, replay summaries on session resume |
| 🆕 | **Truncation Continuation** | Automatic continuation when model response is cut off (`finish_reason=length`) |
| 🆕 | **Ollama Support** | Works out of the box with Ollama's OpenAI-compatible API |
| 🆕 | **LiteLLM Proxy Support** | Route through LiteLLM Proxy to any provider |
| 🆕 | **OpenRouter Support** | Cloud API gateway — access OpenAI, Anthropic, Google models via one endpoint |
| 🆕 | **Query Engine** | Runtime event counters, transcript summaries, orchestration reports |
| 🆕 | **Remote Runtime** | Manifest-backed local remote profiles, connect/disconnect state, and remote CLI/slash flows |
| 🆕 | **Hook & Policy Runtime** | Local `.claw-policy.json` / hook manifests with trust reporting, safe env, tool blocking, and budget overrides |
| 🆕 | **Task & Plan Runtime** | Persistent local tasks and plans with plan-to-task sync and dependency-aware task execution |
| 🆕 | **MCP Transport** | Real stdio MCP transport for `initialize`, resource listing/reading, and tool listing/calling |
| 🆕 | **Search Runtime** | Provider-backed `web_search` with local manifests, activation state, and `/search` flows |
| 🆕 | **Config & Account Runtime** | Local config/settings mutation plus manifest-backed account profiles and login/logout state |
| 🆕 | **Ask-User Runtime** | Queued or interactive local ask-user flow with history, slash commands, and agent tool support |
| 🆕 | **Team Runtime** | Persisted local teams and message history with team/message tools and slash/CLI inspection |
| 🆕 | **Notebook Edit Tool** | Native `.ipynb` cell editing through the real agent tool registry |
| 🆕 | **Workflow Runtime** | Manifest-backed local workflows with workflow tools, slash commands, and run history |
| 🆕 | **Remote Trigger Runtime** | Local remote triggers with create/update/run flows similar to the npm remote trigger surface |
| 🆕 | **Worktree Runtime** | Managed git worktrees with mid-session cwd switching, slash commands, and CLI flows |
| 🆕 | **Tokenizer-Aware Context** | Cached tokenizer backends with heuristic fallback for `/context`, `/status`, and compaction |
| 🆕 | **Prompt Budget Preflight** | Preflight prompt-length validation, token-budget reporting, and auto-compact/context collapse before backend failures |
| 🆕 | **LSP Runtime** | Local LSP-style code intelligence for definitions, references, hover, symbols, call hierarchy, and diagnostics |
| 🆕 | **Local Web GUI** | Browser-based chat UI via `python -m src.gui` — modern dark theme, slash command palette, session browser, settings panel |
| 🆕 | **Pasted-Content Refs** | Pastes ≥500 chars into the GUI composer collapse to `[Pasted text #N +M lines]` chips and re-expand server-side before the agent runs |
| 🆕 | **GUI Runtime Knobs** | Settings panel exposes temperature, per-turn timeout, streaming toggle, and max-turns — all round-tripped live through `/api/state` |
| 🆕 | **GUI Budgets & Limits** | Advanced settings disclosure for every `BudgetConfig` field: cost ceiling, token budgets, tool/model call caps, delegated task cap, session turn cap — blank input clears the limit |
| 🆕 | **GUI System Prompt & Schema** | Custom / append / override system prompts and a structured-output JSON schema editor (with strict toggle) live-editable in the settings panel |
| 🆕 | **GUI Context Management** | Auto-snip / auto-compact thresholds, compact-preserve count, CLAUDE.md discovery toggle, and additional working directories — all editable from the settings panel and the new `--auto-snip-threshold` / `--auto-compact-threshold` / `--add-dir` flags |
| 🆕 | **GUI Tasks View** | Browse, create, start, complete, and cancel local tasks from a new **Tasks** tab; mutations call straight into `TaskRuntime` so completing a task auto-unblocks dependents just like the slash-command path |
| 🆕 | **GUI Plan View** | Edit the local porting plan (steps + explanation + per-step status/priority) from a new **Plan** tab; saves go through `PlanRuntime.update_plan` and optionally sync to the task list |
| 🆕 | **GUI Memory View** | Browse, edit, create, and delete the discovered `CLAUDE.md` / `.claude/rules/*.md` memory files from a new **Memory** tab; writes are sandboxed to the workspace + `~/.claude` |
| 🆕 | **GUI File History View** | New **History** tab aggregates `file_history` entries from every saved session (newest first) — one row per shell run / file edit / nested agent call with snapshot ids and changed paths |
| 🆕 | **GUI Background Sessions** | New **Background** tab lists detached `agent-bg` runs (running/exited/completed/failed), shows live logs, and lets you kill a running session — same `BackgroundSessionRuntime` the CLI uses |
| 🆕 | **GUI Worktree View** | New **Worktree** tab — show status & history, create a managed `git worktree` (auto-switches the agent's cwd), and exit it (keep or remove); state survives reload via `WorktreeRuntime` |
| 🆕 | **GUI Skills Marketplace** | New **Skills** tab — card grid of every bundled skill with description, when-to-use, aliases, and allowed tools; "Use in chat" button drops the invocation into the composer |
| 🆕 | **GUI Accounts View** | New **Accounts** tab — discover profiles from `.claude/account.json`, log in by name or with an ephemeral identity, view login/logout history; persists into `AccountRuntime` state |
| 🆕 | **GUI Remote Profiles** | New **Remote** tab — discover remote/SSH/teleport/direct-connect/deep-link profiles from `.claw-remote.json` etc., connect by name or ephemeral target, view connect/disconnect history |
| 🆕 | **GUI MCP Servers** | New **MCP** tab — list discovered servers/resources/tools from `.claw-mcp.json`/`.mcp.json`, read inline + stdio resources, call tools with custom JSON args; "Probe stdio servers" toggle controls subprocess cost |
| 🆕 | **GUI Plugins View** | New **Plugins** tab — list manifests from `.claw-plugin/plugin.json`, `.codex-plugin/plugin.json`, and `plugins/*/plugin.json` with their tools, virtual tools, aliases, blocks, and lifecycle hooks |
| 🆕 | **GUI Ask-User Queue** | New **Ask** tab — preload answers (exact or contains match), browse the queue and history, and clear past entries; the agent's `Ask` tool consumes them straight from `.port_sessions/ask_user_runtime.json` |
| 🆕 | **GUI Workflows View** | New **Workflows** tab — list discovered workflow definitions from `.claw-workflows.json`, trigger a recorded run with custom JSON arguments, browse run history |
| 🆕 | **Daemon Commands** | Local `daemon start/ps/logs/attach/kill` wrapper over background agent sessions |
| 🆕 | **Background Sessions** | Local `agent-bg`, `agent-ps`, `agent-logs`, `agent-attach`, and `agent-kill` flows |
| 🆕 | **Testing Guide** | Comprehensive [TESTING_GUIDE.md](TESTING_GUIDE.md) with commands for every feature |
| 🆕 | **Parity Checklist** | Full [PARITY_CHECKLIST.md](PARITY_CHECKLIST.md) tracking implementation status vs npm source |

---

## 📖 About

This repository reimplements the [Claude Code](https://docs.anthropic.com/en/docs/claude-code) npm agent architecture **entirely in Python**, designed to run with **local open-source models** via an OpenAI-compatible API server.

Built on the public porting workspace from [instructkr/claw-code](https://github.com/instructkr/claw-code), the active development lives at [HarnessLab/claw-code-agent](https://github.com/HarnessLab/claw-code-agent).

> **Goal:** Not to ship the original npm source, but to reimplement the full agent flow in Python — prompt assembly, context building, slash commands, tool calling, session persistence, and local model execution.
>
> **Zero external dependencies** — just Python's standard library.

<p align="center">
  <img src="images/demo_2.gif" alt="Claw Code Agent demo" width="900" />
</p>

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🤖 **Agent Loop** | Full agentic coding loop with tool calling and iterative reasoning |
| 💬 **Interactive Chat** | Multi-turn REPL via `agent-chat` with session continuity |
| 🖥️ **Local Web GUI** | Browser-based chat UI launched with `python -m src.gui` — sessions browser, slash command palette, live settings |
| 🧰 **Core Tools** | File read / write / edit, glob search, grep search, shell execution |
| 🔌 **Plugin Runtime** | Manifest-based plugins with hooks, aliases, virtual tools, and tool blocking |
| 🪆 **Nested Delegation** | Delegate subtasks to child agents with dependency-aware topological batching |
| 🧩 **Custom Agents** | Load local agent profiles from `~/.claude/agents` and `./.claude/agents`, inspect them via `/agents`, and delegate with `subagent_type` |
| 📡 **Streaming** | Token-by-token streaming output with `--stream` |
| 💬 **Slash Commands** | Local commands for context, config, account, search, MCP, remote, tasks, plan, hooks, and model control |
| 🌐 **Remote Runtime** | Manifest-backed remote profiles with local `remote-mode`, `ssh-mode`, `teleport-mode`, and connect/disconnect state |
| 🧭 **Task & Plan Runtime** | Persistent tasks and plans with sync, next-task selection, and blocked/unblocked state |
| 🛰️ **MCP Runtime** | Local MCP manifests plus real stdio MCP transport for resources and tools |
| 🔎 **Search Runtime** | Provider-backed `web_search` plus provider activation and status reporting |
| ⚙️ **Config & Account Runtime** | Local config mutation, settings inspection, account profiles, and login/logout state |
| 🙋 **Ask-User Runtime** | Queued answer or interactive user-question flow with history tracking |
| 👥 **Team Runtime** | Persisted local teams plus message history, handoff notes, and collaboration metadata |
| 📓 **Notebook Editing** | Native Jupyter notebook cell editing through `notebook_edit` |
| 🪵 **Worktree Runtime** | Managed git worktrees with `worktree_enter`, `worktree_exit`, and live cwd switching |
| 🧭 **Workflow Runtime** | Manifest-backed workflows with slash commands, CLI inspection, and recorded runs |
| ⏰ **Remote Triggers** | Local remote triggers with create/update/run flows and npm-style trigger actions |
| 🪝 **Hook & Policy Runtime** | Trust reporting, safe env, managed settings, tool blocking, and budget overrides |
| 🧠 **LSP Code Intelligence** | Local LSP-style definitions, references, hover, symbols, diagnostics, and call hierarchy |
| 🧠 **Context Engine** | Automatic context building with CLAUDE.md discovery, compaction, and snipping |
| 🔢 **Tokenizer-Aware Accounting** | Model-aware token counting with cached tokenizer backends and fallback heuristics |
| 📏 **Prompt Budgeting** | Soft/hard prompt-window checks, token-budget reports, and preflight context collapse |
| 🔄 **Session Persistence** | Save and resume agent sessions with file-history replay |
| 🗂️ **Background Sessions** | `agent-bg` and local daemon wrappers for background runs, logs, attach, and kill |
| 💰 **Cost & Budget Control** | Token budgets, cost limits, tool-call caps, model-call caps |
| 📋 **Structured Output** | JSON schema response mode for programmatic use |
| 🔐 **Permission System** | Granular control: `--allow-write`, `--allow-shell`, `--unsafe` |
| 🏗️ **OpenAI-Compatible** | Works with vLLM, Ollama, LiteLLM Proxy, OpenRouter — any OpenAI-compatible API |
| 🐉 **Qwen3-Coder** | First-class support for `Qwen3-Coder-30B-A3B-Instruct` via vLLM |
| 📦 **Zero Dependencies** | Pure Python standard library — nothing to install |

---

## 📋 Roadmap

### 📚 Documentation

| Document | Description |
|----------|-------------|
| [TESTING_GUIDE.md](TESTING_GUIDE.md) | Step-by-step commands to verify every feature |
| [PARITY_CHECKLIST.md](PARITY_CHECKLIST.md) | Full implementation status vs the npm source |

### ✅ Done

- [x] Python CLI agent loop
- [x] Interactive chat mode (`agent-chat`) with multi-turn REPL
- [x] OpenAI-compatible local model backend
- [x] Qwen3-Coder support through vLLM with `qwen3_xml` tool parser
- [x] Ollama, LiteLLM Proxy, and OpenRouter backends
- [x] Core tools: `list_dir`, `read_file`, `write_file`, `edit_file`, `glob_search`, `grep_search`, `bash`
- [x] Context building and `/context`-style usage reporting
- [x] Slash commands: `/help`, `/context`, `/context-raw`, `/token-budget`, `/prompt`, `/permissions`, `/model`, `/tools`, `/agents`, `/memory`, `/status`, `/clear`
- [x] Session persistence and `agent-resume` flow
- [x] Permission system (read-only, write, shell, unsafe tiers)
- [x] Streaming token-by-token assistant output
- [x] Truncated-response continuation flow
- [x] Auto-snip and auto-compact context reduction
- [x] Reactive compaction retry on prompt-too-long errors
- [x] Preflight prompt-length validation and token-budget reporting
- [x] Preflight auto-compact/context collapse before backend prompt-too-long failures
- [x] Cost tracking and usage budget enforcement
- [x] Token, tool-call, model-call, and session-turn budgets
- [x] Structured output / JSON schema response mode
- [x] File history journaling with snapshot IDs and replay summaries
- [x] Nested agent delegation with dependency-aware topological batching
- [x] Agent manager with lineage tracking and group membership
- [x] Filesystem-backed custom agent profiles with built-in/user/project precedence
- [x] Local custom-agent create/update/delete flows via CLI and `/agents`
- [x] Local daemon-style background command family
- [x] Local background session workflows: `agent-bg`, `agent-ps`, `agent-logs`, `agent-attach`, `agent-kill`
- [x] Local remote runtime: manifest discovery, profile listing, connect/disconnect persistence, and CLI/slash flows
- [x] Local hook and policy runtime with trust reporting, safe env, tool blocking, and budget overrides
- [x] Local config runtime: config discovery, effective settings, source inspection, and config mutation
- [x] Local LSP runtime: definitions, references, hover, symbols, diagnostics, and call hierarchy
- [x] Local account runtime: profile discovery, login/logout state, and account CLI/slash flows
- [x] Local ask-user runtime: queued answers, history, and ask-user CLI/slash flows
- [x] Local team runtime: persisted teams, team messages, and team CLI/slash flows
- [x] Local search runtime with provider discovery, activation, and provider-backed `web_search`
- [x] Local MCP runtime: manifest resources, stdio transport, MCP resources, and MCP tool calls
- [x] Local task and plan runtimes with plan sync and dependency-aware task execution
- [x] Notebook edit tool in the real Python tool registry
- [x] Local workflow runtime with workflow list/get/run tools and CLI/slash flows
- [x] Local remote trigger runtime with create/update/run flows and CLI/slash inspection
- [x] Local managed git worktree runtime with live cwd switching and worktree CLI/slash flows
- [x] Local web GUI (FastAPI + vanilla JS SPA) with chat, sessions browser, slash command palette, and live settings (`python -m src.gui`)
- [x] Tokenizer-aware context accounting with cached tokenizer backends and heuristic fallback
- [x] Plugin runtime: manifest discovery, hooks, aliases, virtual tools, tool blocking
- [x] Plugin lifecycle hooks: resume, persist, delegate phases
- [x] Plugin session-state persistence and resume restoration
- [x] Query engine facade driving the real Python runtime
- [x] Compaction metadata with lineage IDs and revision summaries
- [x] Extended runtime tools: `web_fetch`, `web_search`, `tool_search`, `sleep`
- [x] Unit tests for the Python runtime
- [x] `pyproject.toml` packaging with `setuptools`

### 🔲 In Progress

- [ ] Full MCP parity beyond the current stdio transport and local manifest/resource/tool support
- [ ] Full slash-command parity with npm runtime
- [ ] Full interactive REPL / TUI behavior
- [ ] Full tokenizer/chat-message framing parity beyond the current tokenizer-aware accounting
- [ ] Hooks system parity
- [ ] Real remote transport/runtime parity beyond the current local remote-profile runtime
- [ ] Voice and VIM modes
- [ ] Editor and platform integrations
- [ ] Background and team features

---

## 🏗️ Architecture

```text
claw-code/
├── README.md
├── TESTING_GUIDE.md              # How to test every feature
├── PARITY_CHECKLIST.md           # Implementation status vs npm source
├── pyproject.toml
├── .gitignore
├── images/
│   └── logo.png
├── src/                          # Python implementation
│   ├── main.py                   # CLI entry point & argument parsing
│   ├── agent_runtime.py          # Core agent loop (LocalCodingAgent)
│   ├── agent_tools.py            # Tool definitions & execution engine
│   ├── agent_prompting.py        # System prompt assembly
│   ├── agent_registry.py         # Built-in + filesystem-backed custom agent discovery
│   ├── agent_context.py          # Context building & CLAUDE.md discovery
│   ├── agent_context_usage.py    # Context usage estimation & reporting
│   ├── agent_session.py          # Session state management
│   ├── agent_slash_commands.py   # Local slash command processing
│   ├── agent_manager.py          # Nested agent lineage & group tracking
│   ├── agent_types.py            # Shared dataclasses & type definitions
│   ├── openai_compat.py          # OpenAI-compatible API client (streaming)
│   ├── plugin_runtime.py         # Plugin manifest, hooks, aliases, virtual tools
│   ├── agent_plugin_cache.py     # Plugin discovery & prompt injection cache
│   ├── session_store.py          # Session serialization & persistence
│   ├── transcript.py             # Transcript block export & mutation tracking
│   ├── query_engine.py           # Query engine facade & runtime orchestration
│   ├── mcp_runtime.py            # Local MCP discovery and stdio MCP transport
│   ├── search_runtime.py         # Search providers and provider-backed web_search
│   ├── remote_runtime.py         # Local remote profiles, connect/disconnect state, remote CLI support
│   ├── background_runtime.py     # Local background sessions and daemon support
│   ├── account_runtime.py        # Local account profiles, login/logout state, account CLI support
│   ├── ask_user_runtime.py       # Local ask-user queued answers and interaction history
│   ├── config_runtime.py         # Local workspace config/settings discovery and mutation
│   ├── lsp_runtime.py            # Local LSP-style code intelligence and diagnostics
│   ├── token_budget.py           # Prompt-window budgeting and preflight prompt-length validation
│   ├── plan_runtime.py           # Persistent plan runtime and plan sync
│   ├── task_runtime.py           # Persistent task runtime and task execution
│   ├── task.py                   # Task state model and task dataclasses
│   ├── team_runtime.py           # Local teams, messages, and collaboration metadata
│   ├── workflow_runtime.py       # Local workflow manifests and recorded workflow runs
│   ├── remote_trigger_runtime.py # Local remote trigger manifests and trigger run history
│   ├── worktree_runtime.py       # Managed git worktree sessions and cwd switching
│   ├── hook_policy.py            # Hook/policy manifests, trust, and safe env handling
│   ├── tokenizer_runtime.py      # Tokenizer-aware context accounting backends
│   ├── permissions.py            # Tool permission filtering
│   ├── cost_tracker.py           # Cost & budget enforcement
│   ├── commands.py               # Mirrored command inventory
│   ├── tools.py                  # Mirrored tool inventory
│   ├── runtime.py                # Mirrored runtime facade
│   ├── reference_data/           # Mirrored inventory snapshots
│   └── gui/                      # Local web GUI (FastAPI + vanilla JS SPA)
│       ├── __main__.py           # `python -m src.gui` entry point
│       ├── server.py             # FastAPI app and JSON endpoints
│       └── static/               # index.html, app.css, app.js
└── tests/                        # Unit tests
    ├── test_agent_runtime.py
    ├── test_agent_context.py
    ├── test_agent_context_usage.py
    ├── test_agent_prompting.py
    ├── test_agent_slash_commands.py
    ├── test_main.py
    ├── test_query_engine_runtime.py
    └── test_porting_workspace.py
```

---

## 📦 Requirements

| Requirement | Details |
|-------------|---------|
| 🐍 Python | `3.10` or higher |
| 📚 Dependencies | **None** — pure Python standard library |
| 🖥️ Model Server | `vLLM`, `Ollama`, `LiteLLM Proxy`, or `OpenRouter`, with tool calling support |
| 🧠 Model | [`Qwen/Qwen3-Coder-30B-A3B-Instruct`](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct) (recommended) |

---

## 🚀 Quick Start

### 1. Start vLLM with Qwen3-Coder

vLLM must be started with automatic tool choice enabled. Use the `qwen3_xml` parser for Qwen3-Coder tool calling:

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen3-Coder-30B-A3B-Instruct \
  --host 127.0.0.1 \
  --port 8000 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_xml
```

Verify the server is running:

```bash
curl http://127.0.0.1:8000/v1/models
```

> 📚 **References:** [vLLM Tool Calling Docs](https://docs.vllm.ai/en/v0.13.0/features/tool_calling/) · [OpenAI-Compatible Server](https://docs.vllm.ai/en/v0.13.0/serving/openai_compatible_server.html)

### Optional: Use Ollama Instead of vLLM

`claw-code-agent` can also work with Ollama because the runtime targets an OpenAI-compatible API. Use a model that supports tool calling well.

Example:

```bash
ollama serve
ollama pull qwen3
```

Then configure:

```bash
export OPENAI_BASE_URL=http://127.0.0.1:11434/v1
export OPENAI_API_KEY=ollama
export OPENAI_MODEL=qwen3
```

Notes:

- prefer tool-capable models such as `qwen3`
- plain chat-only models are not enough for full agent behavior
- Ollama does not use the `vLLM` parser flags shown above

> 📚 **References:** [Ollama OpenAI Compatibility](https://docs.ollama.com/api/openai-compatibility) · [Ollama Tool Calling](https://docs.ollama.com/capabilities/tool-calling)

### Optional: Use LiteLLM Proxy

`claw-code-agent` can also work through LiteLLM Proxy because the runtime targets an OpenAI-compatible chat completions API. The routed model still needs to support tool calling for full agent behavior.

Quick start example:

```bash
pip install 'litellm[proxy]'
litellm --model ollama/qwen3
```

LiteLLM Proxy runs on port `4000` by default. Then configure:

```bash
export OPENAI_BASE_URL=http://127.0.0.1:4000
export OPENAI_API_KEY=anything
export OPENAI_MODEL=ollama/qwen3
```

Notes:

- LiteLLM Proxy gives you an OpenAI-style gateway in front of many providers
- tool use still depends on the underlying routed model and provider behavior
- if you configure a LiteLLM master key, use that instead of `anything`

> 📚 **References:** [LiteLLM Docs](https://docs.litellm.ai/) · [LiteLLM Proxy Quick Start](https://docs.litellm.ai/)

### Optional: Use OpenRouter

`claw-code-agent` can also work with [OpenRouter](https://openrouter.ai/), a cloud API gateway that provides access to models from OpenAI, Anthropic, Google, Meta, and others through a single OpenAI-compatible endpoint. No local model server required.

Configure:

```bash
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
export OPENAI_API_KEY=sk-or-v1-your-key-here
export OPENAI_MODEL=openai/gpt-4o-mini
```

Notes:

- sign up at [openrouter.ai](https://openrouter.ai/) and create an API key under [Keys](https://openrouter.ai/keys)
- model names use the `provider/model` format (e.g. `anthropic/claude-sonnet-4`, `openai/gpt-4o`, `google/gemini-2.5-pro`)
- tool calling support varies by model — check the [model list](https://openrouter.ai/models) for capabilities
- this sends your conversation (including file contents and shell output) to OpenRouter and the upstream provider — do not use with repos containing secrets or sensitive data

> 📚 **References:** [OpenRouter Docs](https://openrouter.ai/docs) · [Supported Models](https://openrouter.ai/models) · [API Keys](https://openrouter.ai/keys)

### 2. Configure Environment

```bash
export OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export OPENAI_API_KEY=local-token
export OPENAI_MODEL=Qwen/Qwen3-Coder-30B-A3B-Instruct
```

### Use Another Model With vLLM

If you want to try another model, keep the same `vLLM` server setup and change the `--model` value when you launch `vLLM`.

Example:

```bash
python -m vllm.entrypoints.openai.api_server \
  --model your-model-name \
  --host 127.0.0.1 \
  --port 8000 \
  --enable-auto-tool-choice \
  --tool-call-parser your_parser
```

Then update:

```bash
export OPENAI_MODEL=your-model-name
```

Notes:

- the documented path in this repository is `vLLM`
- the model must support tool calling well enough for agent use
- some model families require a different `--tool-call-parser`
- slash commands such as `/help`, `/context`, and `/tools` are local and do not require the model server

### 3. Run the Agent

```bash
# Read-only question
python3 -m src.main agent \
  "Read src/agent_runtime.py and summarize how the loop works." \
  --cwd .

# Write-enabled task
python3 -m src.main agent \
  "Create TEST_QWEN_AGENT.md with one line: test ok" \
  --cwd . --allow-write

# Shell-enabled task
python3 -m src.main agent \
  "Run pwd and ls src, then summarize the result." \
  --cwd . --allow-shell

# Interactive chat mode
python3 -m src.main agent-chat --cwd .

# Streaming output
python3 -m src.main agent \
  "Explain the current architecture." \
  --cwd . --stream
```

---

## 🛠️ Usage

### Agent Commands

| Command | Description |
|---------|-------------|
| `agent <prompt>` | Run the agent with a prompt |
| `agent-chat [prompt]` | Start interactive multi-turn chat mode |
| `agent-bg <prompt>` | Run the agent in a local background session |
| `agent-ps` | List local background sessions |
| `agent-logs <id>` | Show background session logs |
| `agent-attach <id>` | Show the current background output snapshot |
| `agent-kill <id>` | Stop a background session |
| `daemon <subcommand>` | Daemon-style wrapper over local background sessions |
| `agent-prompt` | Show the assembled system prompt |
| `agent-context` | Show estimated context usage |
| `agent-context-raw` | Show the raw context snapshot |
| `token-budget` | Show prompt-window budget, reserves, and soft/hard input limits |
| `agents [agent_type]` | List active local agent definitions or show one agent profile |
| `agents-create <agent_type>` | Create a project or user agent definition markdown file |
| `agents-update <agent_type>` | Update an existing project or user agent definition |
| `agents-delete <agent_type>` | Delete an existing project or user agent definition |
| `agent-resume <id> <prompt>` | Resume a saved session |

### Runtime Utility Commands

| Command | Description |
|---------|-------------|
| `search-status` / `search-providers` / `search-activate` / `search` | Inspect and use the local search runtime |
| `mcp-status` / `mcp-resources` / `mcp-resource` / `mcp-tools` / `mcp-call-tool` | Inspect and use the local MCP runtime |
| `remote-status` / `remote-profiles` / `remote-disconnect` | Inspect local remote runtime state |
| `remote-mode` / `ssh-mode` / `teleport-mode` / `direct-connect-mode` / `deep-link-mode` | Activate local remote runtime modes |
| `config-status` / `config-effective` / `config-source` / `config-get` / `config-set` | Inspect and mutate local config/settings |
| `account-status` / `account-profiles` / `account-login` / `account-logout` | Inspect and mutate local account state |

### CLI Flags

| Flag | Description |
|------|-------------|
| `--cwd <path>` | Set the workspace directory |
| `--model <name>` | Override the model name |
| `--base-url <url>` | Override the API base URL |
| `--allow-write` | Allow the agent to modify files |
| `--allow-shell` | Allow the agent to execute shell commands |
| `--unsafe` | Allow destructive shell operations |
| `--stream` | Enable token-by-token streaming output |
| `--show-transcript` | Print the full message transcript |
| `--scratchpad-root <path>` | Override the scratchpad directory |
| `--system-prompt <text>` | Set a custom system prompt |
| `--append-system-prompt <text>` | Append to the system prompt |
| `--override-system-prompt <text>` | Replace the generated system prompt |
| `--add-dir <path>` | Add extra directories to context |

### Budget & Limit Flags

| Flag | Description |
|------|-------------|
| `--max-total-tokens <n>` | Total token budget |
| `--max-input-tokens <n>` | Input token budget |
| `--max-output-tokens <n>` | Output token budget |
| `--max-reasoning-tokens <n>` | Reasoning token budget |
| `--max-budget-usd <n>` | Maximum cost in USD |
| `--max-tool-calls <n>` | Maximum tool calls per run |
| `--max-delegated-tasks <n>` | Maximum delegated subtasks |
| `--max-model-calls <n>` | Maximum model API calls |
| `--max-session-turns <n>` | Maximum session turns |
| `--input-cost-per-million <n>` | Input token pricing |
| `--output-cost-per-million <n>` | Output token pricing |

### Context Control Flags

| Flag | Description |
|------|-------------|
| `--auto-snip-threshold <n>` | Auto-snip older messages at this token count |
| `--auto-compact-threshold <n>` | Auto-compact at this token count |
| `--compact-preserve-messages <n>` | Messages to preserve during compaction |
| `--disable-claude-md` | Disable CLAUDE.md discovery |

### Structured Output Flags

| Flag | Description |
|------|-------------|
| `--response-schema-file <path>` | JSON schema file for structured output |
| `--response-schema-name <name>` | Schema name identifier |
| `--response-schema-strict` | Enforce strict schema validation |

### Slash Commands

These are handled **locally** before the model loop:

| Command | Aliases | Description |
|---------|---------|-------------|
| `/help` | `/commands` | Show built-in slash commands |
| `/context` | `/usage` | Show estimated session context usage |
| `/context-raw` | `/env` | Show raw environment & context snapshot |
| `/token-budget` | `/budget` | Show prompt-window budget, reserves, and soft/hard input limits |
| `/mcp` | — | Show MCP runtime status, tools, or a single MCP tool |
| `/resources` | — | List MCP resources |
| `/resource` | — | Read an MCP resource by URI |
| `/search` | — | Show search status, providers, activate a provider, or run a search |
| `/remote` | — | Show local remote status or activate a target |
| `/remotes` | — | List local remote profiles |
| `/ssh` | — | Activate an SSH-style remote profile |
| `/teleport` | — | Activate a teleport-style remote profile |
| `/direct-connect` | — | Activate a direct-connect remote profile |
| `/deep-link` | — | Activate a deep-link remote profile |
| `/disconnect` | `/remote-disconnect` | Disconnect the active remote runtime target |
| `/account` | — | Show account runtime status or profiles |
| `/login` | — | Activate a local account profile or identity |
| `/logout` | — | Clear the active account session |
| `/config` | `/settings` | Inspect effective config, sources, or a single config value |
| `/plan` | `/planner` | Show the local plan runtime state |
| `/tasks` | `/todo` | Show the local task list |
| `/task` | — | Show a task by id |
| `/task-next` | `/next-task` | Show the next actionable tasks |
| `/prompt` | `/system-prompt` | Render the effective system prompt |
| `/hooks` | `/policy` | Show local hook/policy manifests |
| `/trust` | — | Show trust mode, managed settings, and safe env values |
| `/permissions` | — | Show active tool permission mode |
| `/model` | — | Show or update the active model |
| `/tools` | — | List registered tools with permission status |
| `/agents` | — | List, show, create, update, or delete local agent definitions |
| `/memory` | — | Show loaded CLAUDE.md memory bundle |
| `/status` | `/session` | Show runtime/session status summary |
| `/clear` | — | Clear ephemeral runtime state |

```bash
python3 -m src.main agent "/help"
python3 -m src.main agent "/context" --cwd .
python3 -m src.main agent "/token-budget" --cwd .
python3 -m src.main agent "/tools" --cwd .
python3 -m src.main agent "/agents" --cwd .
python3 -m src.main agent "/status" --cwd .
```

### Custom Agent Definitions

Custom agent profiles can live in either of these directories:

- `./.claude/agents/*.md`
- `~/.claude/agents/*.md`

Project agents override user agents, and user agents override built-ins when the `agent_type` matches.

Example agent file:

```md
---
name: reviewer
description: "Review implementation changes carefully."
tools: read_file, grep_search
model: Qwen/Qwen3-Coder-30B-A3B-Instruct
initialPrompt: Start by identifying the highest-risk files.
---

Inspect code changes and summarize correctness risks, regressions, and missing tests.
```

Inspect the loaded profiles:

```bash
python3 -m src.main agents --cwd .
python3 -m src.main agents reviewer --cwd .
python3 -m src.main agent "/agents" --cwd .
python3 -m src.main agent "/agents show reviewer" --cwd .
```

Create, update, or delete agent files from the CLI:

```bash
python3 -m src.main agents-create reviewer \
  --cwd . \
  --description "Review implementation changes carefully." \
  --prompt "Inspect code changes and summarize risks." \
  --tools read_file,grep_search \
  --model Qwen/Qwen3-Coder-30B-A3B-Instruct

python3 -m src.main agents-update reviewer \
  --cwd . \
  --description "Review implementation changes and tests carefully." \
  --prompt "Focus on regressions, missing tests, and risky diffs."

python3 -m src.main agents-delete reviewer --cwd . --source project
```

Or use the local slash command management forms:

```bash
python3 -m src.main agent "/agents create reviewer :: Review implementation changes carefully. :: Inspect code changes and summarize risks." --cwd .
python3 -m src.main agent "/agents update reviewer Updated review description :: Focus on regressions and missing tests." --cwd .
python3 -m src.main agent "/agents delete reviewer" --cwd .
```

### Utility Commands

```bash
python3 -m src.main summary            # Workspace summary
python3 -m src.main manifest           # Workspace manifest
python3 -m src.main commands --limit 10 # Command inventory
python3 -m src.main tools --limit 10    # Tool inventory
```

---

## 🔧 Built-in Tools

The runtime currently includes core and extended tools:

| Tool | Description | Permission |
|------|-------------|------------|
| `list_dir` | List files and directories | 🟢 Always |
| `read_file` | Read file contents (with line ranges) | 🟢 Always |
| `write_file` | Write or create files | 🟡 `--allow-write` |
| `edit_file` | Edit files via exact string matching | 🟡 `--allow-write` |
| `glob_search` | Find files by glob pattern | 🟢 Always |
| `grep_search` | Search file contents by regex | 🟢 Always |
| `bash` | Execute shell commands | 🔴 `--allow-shell` |
| `web_fetch` | Fetch local or remote text content by URL | 🟢 Always |
| `search_status` / `search_list_providers` / `search_activate_provider` / `web_search` | Search runtime status and provider-backed web search | 🟢 Always |
| `tool_search` | Search the current Python tool registry | 🟢 Always |
| `sleep` | Bounded local wait tool | 🟢 Always |
| `config_list` / `config_get` / `config_set` | Inspect and mutate local workspace config | `config_set` is 🟡 `--allow-write` |
| `account_status` / `account_list_profiles` / `account_login` / `account_logout` | Inspect and mutate local account state | 🟢 Always |
| `remote_status` / `remote_list_profiles` / `remote_connect` / `remote_disconnect` | Inspect and mutate local remote runtime state | 🟢 Always |
| `mcp_list_resources` / `mcp_read_resource` / `mcp_list_tools` / `mcp_call_tool` | Use local MCP resources and transport-backed MCP tools | 🟢 Always |
| `plan_get` / `update_plan` / `plan_clear` | Inspect and mutate the local plan runtime | `update_plan` is 🟡 `--allow-write` |
| `task_next` / `task_list` / `task_get` / `task_create` / `task_update` / `task_start` / `task_complete` / `task_block` / `task_cancel` / `todo_write` | Persistent local task and todo management | write-like task mutations are 🟡 `--allow-write` |
| `delegate_agent` | Delegate work to nested child agents | 🟢 Always |

---

## 🔌 Plugin System

Claw Code Agent supports a **manifest-based plugin runtime**. Drop a `plugin.json` in a `plugins/` subdirectory:

```json
{
  "name": "my-plugin",
  "hooks": {
    "beforePrompt": "Inject guidance into the system prompt.",
    "afterTurn": "Run after each agent turn.",
    "onResume": "Reapply state on session resume.",
    "beforePersist": "Save state before session is saved.",
    "beforeDelegate": "Inject guidance before child agents.",
    "afterDelegate": "Process child agent results."
  },
  "toolAliases": [
    { "name": "my_read", "baseTool": "read_file", "description": "Custom read alias." }
  ],
  "virtualTools": [
    { "name": "my_tool", "description": "A virtual tool.", "responseTemplate": "result: {input}" }
  ]
}
```

> See [TESTING_GUIDE.md](TESTING_GUIDE.md) **Section 19** for full plugin testing commands.

---

## 🪆 Nested Agent Delegation

The agent can delegate subtasks to child agents with full context carryover:

```bash
python3 -m src.main agent \
  "Delegate a subtask to inspect src/agent_runtime.py and return a summary." \
  --cwd . --show-transcript
```

Features:
- Sequential and parallel subtask execution
- Dependency-aware topological batching
- Child-session save and resume
- Agent manager lineage tracking

> See [TESTING_GUIDE.md](TESTING_GUIDE.md) **Section 20** for delegation testing commands.

---

## 🖥️ Local Web GUI

If the terminal isn't your thing, launch the bundled browser GUI:

```bash
python3 -m src.gui --cwd . --allow-write --allow-shell
```

Your default browser opens to `http://127.0.0.1:8765` with a modern dark-themed chat UI.

| Flag | Description |
|------|-------------|
| `--host <addr>` | Bind address (default `127.0.0.1`) |
| `--port <n>` | Port to listen on (default `8765`) |
| `--cwd <path>` | Workspace directory the agent operates in |
| `--model <name>` | Override the model name |
| `--base-url <url>` | Override the OpenAI-compatible API base URL |
| `--api-key <key>` | API key for the model server |
| `--session-dir <path>` | Where saved sessions live |
| `--allow-write` | Allow file write/edit tools |
| `--allow-shell` | Allow shell execution |
| `--temperature <f>` | Sampling temperature (default `0.0`) |
| `--timeout-seconds <f>` | Per-turn model timeout in seconds (default `120`) |
| `--stream` | Enable streaming model responses |
| `--max-turns <n>` | Per-run turn limit (default `12`) |
| `--max-budget-usd <f>` | Abort the run if total cost exceeds this |
| `--max-total-tokens <n>` | Token budget across prompt + completion |
| `--max-input-tokens <n>` | Input-token cap per call |
| `--max-output-tokens <n>` | Output-token cap per call |
| `--max-reasoning-tokens <n>` | Reasoning-token cap per call |
| `--max-tool-calls <n>` | Hard cap on tool invocations per run |
| `--max-model-calls <n>` | Hard cap on model invocations per run |
| `--max-delegated-tasks <n>` | Cap on nested delegated agents |
| `--max-session-turns <n>` | Cap across resumed sessions |
| `--system-prompt <s>` | Replace the rendered system prompt body |
| `--append-system-prompt <s>` | Append text to the rendered system prompt |
| `--override-system-prompt <s>` | Skip the default system prompt entirely and use this |
| `--response-schema-file <path>` | Load a structured-output schema from a JSON file |
| `--response-schema-name <s>` | Name the schema (default `response`) |
| `--response-schema-strict` | Reject responses that don't match the schema |
| `--auto-snip-threshold <n>` | Token threshold above which old messages are auto-snipped |
| `--auto-compact-threshold <n>` | Token threshold above which the conversation is auto-compacted |
| `--compact-preserve-messages <n>` | Number of recent messages preserved during a compact (default `4`) |
| `--disable-claude-md` | Skip discovery of `CLAUDE.md` files |
| `--add-dir <path>` | Additional working directory the agent may operate in (repeatable) |
| `--no-browser` | Don't auto-open a browser tab |

Every budget flag above is also editable at runtime through the **Budgets & limits** disclosure in the settings panel — leave a field blank to clear the limit, type a number to set it.

The GUI surfaces:

- multi-turn chat with tool-call cards (collapsible JSON args + results)
- saved sessions sidebar with one-click resume
- slash command and skill pickers (`/` and `★` buttons, or `Cmd/Ctrl+K`)
- live settings panel (model, base URL, working dir, permissions)
- usage / cost meta in the composer footer
- pasted-content collapsing — see below
- runtime knobs: temperature, timeout, streaming toggle, max turns
- a **Tasks** tab in the topbar — list / create / start / complete / cancel against `.port_sessions/task_runtime.json`

### Paste large content

Paste anything ≥500 characters into the composer (a logfile, a stack trace, an entire file) and the GUI replaces it with a short reference like `[Pasted text #1 +42 lines]`, plus a chip above the textarea showing `📎 [Pasted text #1] · 42 lines · 1894 chars · ✕`.

- The reference stays editable — type around it, delete it, or duplicate it; whatever survives at send-time is what gets expanded.
- The full content is held in the browser only and shipped with the next `/api/chat` request as `pasted_contents`.
- The server re-splices the original text back in before the agent runs, so the model sees the full payload — never the placeholder.
- The chip's `✕` button drops both the content stash and any inline ref so it can't accidentally come along.
- The stash clears after every successful send and when you click `+ New chat`.

> **Note:** The GUI uses [FastAPI](https://fastapi.tiangolo.com/) and [Uvicorn](https://www.uvicorn.org/) under the hood. These get installed automatically if you install the package via `pip install -e .`. The core Python agent runtime itself remains dependency-free.

---

## 🔄 Session Persistence

Each `agent` run automatically saves a resumable session:

```text
session_id=4f2c8c6f9c0e4d7c9c7b1b2a3d4e5f67
session_path=.port_sessions/agent/4f2c8c6f...
```

Resume a previous session:

```bash
python3 -m src.main agent-resume \
  4f2c8c6f9c0e4d7c9c7b1b2a3d4e5f67 \
  "Continue the previous task and finish the missing parts."
```

Resume directly into interactive chat:

```bash
python3 -m src.main agent-chat \
  --resume-session-id <session-id> \
  --cwd .
```

Inspect saved sessions:

```bash
ls -lt .port_sessions/agent
```

> **Note:** Run `agent-resume` from the same `claw-code/` directory where the session was created. A resumed session continues from the saved transcript, not from scratch.

---

## 🧪 Testing

Run the full test suite:

```bash
python3 -m unittest discover -s tests -v
```

Smoke tests:

```bash
python3 -m src.main agent "/help"
python3 -m src.main agent-context --cwd .
python3 -m src.main agent \
  "Read src/agent_session.py and summarize the message flow." \
  --cwd .
```

> 📚 **Full testing guide:** See [TESTING_GUIDE.md](TESTING_GUIDE.md) for step-by-step commands covering the full implemented runtime surface.

---

## 🔐 Permission Model

Claw Code Agent uses a **tiered permission system** to keep the agent safe by default:

| Tier | Capability | Flag Required |
|------|-----------|---------------|
| **Read-only** | List, read, glob, grep | None (default) |
| **Write** | + file creation and editing | `--allow-write` |
| **Shell** | + shell command execution | `--allow-shell` |
| **Unsafe** | + destructive shell operations | `--unsafe` |

---

## 🔎 Parity Status

The full implementation checklist tracking parity against the npm `src` lives in [PARITY_CHECKLIST.md](PARITY_CHECKLIST.md).

It covers: core runtime, CLI modes, prompt assembly, context/memory, slash commands, tools, permissions, plugins, MCP, REPL/TUI, remote features, editor integrations, and internal subsystems.

---

## ⚠️ Disclaimer

- This repository is a **Python reimplementation** inspired by the Claude Code npm architecture.
- It does **not** ship the original npm source.
- It is **not** affiliated with or endorsed by Anthropic.

---

<p align="center">
  <sub>Built with 🐍 Python · Powered by 🐉 HarnessLab Team.</sub>
</p>
