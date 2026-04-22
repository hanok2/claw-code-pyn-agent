"use strict";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
const State = {
  serverState: null,
  sessions: [],
  slashCommands: [],
  skills: [],
  activeSessionId: null,   // the session we will resume on next send
  isBusy: false,
  paletteMode: null,       // "slash" | "skills" | null
  // Pasted content keyed by ref id.  Cleared after each send.  Mirrors the
  // npm front-end's `[Pasted text #N]` collapsing — large pastes never sit
  // inline in the textarea, only the placeholder ref does.
  pastedContents: {},
  nextPasteId: 1,
};

// Paste larger than this many characters gets collapsed to a [Pasted text #N]
// reference.  500 is what the npm front-end uses for its truncation threshold.
const PASTE_COLLAPSE_THRESHOLD = 500;

// ---------------------------------------------------------------------------
// DOM refs
// ---------------------------------------------------------------------------
const $ = (sel) => document.querySelector(sel);
const els = {
  chat: $("#chat"),
  welcome: $("#welcome"),
  input: $("#prompt-input"),
  sendBtn: $("#send-btn"),
  sessionList: $("#session-list"),
  newSessionBtn: $("#new-session-btn"),
  settingsForm: $("#settings-form"),
  statusDot: $("#status-dot"),
  statusText: $("#status-text"),
  cwdMeta: $("#cwd-meta"),
  usageMeta: $("#usage-meta"),
  slashBtn: $("#slash-btn"),
  skillsBtn: $("#skills-btn"),
  clearBtn: $("#clear-btn"),
  palette: $("#palette"),
  paletteSearch: $("#palette-search"),
  paletteList: $("#palette-list"),
  paletteClose: $("#palette-close"),
  pasteChips: $("#paste-chips"),
  tasksView: $("#tasks-view"),
  tasksCreate: $("#tasks-create"),
  tasksList: $("#tasks-list"),
  tasksCounts: $("#tasks-counts"),
  tasksRefresh: $("#tasks-refresh"),
  viewTabs: document.querySelectorAll(".view-tab"),
  planSteps: $("#plan-steps"),
  planExplanation: $("#plan-explanation"),
  planMeta: $("#plan-meta"),
  planSave: $("#plan-save"),
  planClear: $("#plan-clear"),
  planRefresh: $("#plan-refresh"),
  planAddStep: $("#plan-add-step"),
  planSyncTasks: $("#plan-sync-tasks"),
  memoryList: $("#memory-list"),
  memoryContent: $("#memory-content"),
  memoryCurrent: $("#memory-current"),
  memoryFlags: $("#memory-flags"),
  memorySave: $("#memory-save"),
  memoryDelete: $("#memory-delete"),
  memoryRefresh: $("#memory-refresh"),
  memoryNew: $("#memory-new"),
  historyList: $("#history-list"),
  historyMeta: $("#history-meta"),
  historyRefresh: $("#history-refresh"),
  bgList: $("#bg-list"),
  bgCounts: $("#bg-counts"),
  bgRefresh: $("#bg-refresh"),
  bgCurrent: $("#bg-current"),
  bgFlags: $("#bg-flags"),
  bgKill: $("#bg-kill"),
  bgLogs: $("#bg-logs"),
  bgLogsRefresh: $("#bg-logs-refresh"),
  worktreeStatus: $("#worktree-status"),
  worktreeRefresh: $("#worktree-refresh"),
  worktreeEnterForm: $("#worktree-enter-form"),
  worktreeExit: $("#worktree-exit"),
  worktreeExitAction: $("#worktree-exit-action"),
  worktreeDiscard: $("#worktree-discard"),
  worktreeHistory: $("#worktree-history"),
  skillsGrid: $("#skills-grid"),
  skillsRefresh: $("#skills-refresh"),
  skillsIncludeInternal: $("#skills-include-internal"),
};

const BgState = { current: null, status: null };

const MemoryState = { current: null, writable: false, dirty: false };

const PLAN_STATUSES = ["pending", "in_progress", "completed", "blocked", "cancelled"];

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------
async function apiGet(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

async function apiPost(path, body) {
  const r = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body == null ? "{}" : JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok && !data.error) {
    throw new Error(data.detail || `${r.status} ${r.statusText}`);
  }
  return data;
}

// ---------------------------------------------------------------------------
// Markdown rendering (small, dependency-free)
// ---------------------------------------------------------------------------
function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderMarkdown(md) {
  if (md == null) return "";
  // Pull fenced code blocks out first so their contents are not parsed.
  const codeBlocks = [];
  let text = String(md).replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (_, lang, body) => {
    const idx = codeBlocks.length;
    codeBlocks.push({ lang, body });
    return `\u0000CODE${idx}\u0000`;
  });
  text = escapeHtml(text);
  // Headings
  text = text.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  text = text.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  text = text.replace(/^# (.+)$/gm, "<h1>$1</h1>");
  // Bold / italic
  text = text.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/(^|\W)\*([^*\n]+)\*(\W|$)/g, "$1<em>$2</em>$3");
  // Inline code
  text = text.replace(/`([^`\n]+)`/g, "<code>$1</code>");
  // Links
  text = text.replace(
    /\[([^\]]+)\]\(([^)\s]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener">$1</a>'
  );
  // Lists (simple, line-based)
  text = text.replace(/(?:^|\n)((?:- .+\n?)+)/g, (_, block) => {
    const items = block
      .trim()
      .split(/\n/)
      .map((l) => `<li>${l.replace(/^- /, "")}</li>`)
      .join("");
    return `\n<ul>${items}</ul>\n`;
  });
  text = text.replace(/(?:^|\n)((?:\d+\. .+\n?)+)/g, (_, block) => {
    const items = block
      .trim()
      .split(/\n/)
      .map((l) => `<li>${l.replace(/^\d+\. /, "")}</li>`)
      .join("");
    return `\n<ol>${items}</ol>\n`;
  });
  // Paragraphs (split on blank lines)
  text = text
    .split(/\n{2,}/)
    .map((chunk) => {
      const t = chunk.trim();
      if (!t) return "";
      if (/^<(h\d|ul|ol|pre|blockquote)/.test(t)) return t;
      return `<p>${t.replace(/\n/g, "<br/>")}</p>`;
    })
    .join("\n");
  // Restore code blocks
  text = text.replace(/\u0000CODE(\d+)\u0000/g, (_, idx) => {
    const { lang, body } = codeBlocks[Number(idx)];
    const langClass = lang ? ` class="lang-${escapeHtml(lang)}"` : "";
    return `<pre><code${langClass}>${escapeHtml(body)}</code></pre>`;
  });
  return text;
}

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------
function setStatus(state, text) {
  els.statusDot.classList.remove("busy", "error");
  if (state === "busy") els.statusDot.classList.add("busy");
  if (state === "error") els.statusDot.classList.add("error");
  els.statusText.textContent = text;
}

function setBusy(busy) {
  State.isBusy = busy;
  els.sendBtn.disabled = busy;
  els.input.disabled = busy;
  if (busy) setStatus("busy", "Working…");
  else setStatus("ready", "Ready");
}

function clearChat() {
  els.chat.innerHTML = "";
  if (els.welcome) {
    els.chat.appendChild(els.welcome);
  }
}

function hideWelcome() {
  if (els.welcome && els.welcome.parentElement) {
    els.welcome.remove();
  }
}

function avatarFor(role) {
  if (role === "user") return "U";
  if (role === "assistant") return "AI";
  if (role === "tool") return "⚙";
  if (role === "error") return "!";
  return "•";
}

function appendMessage({ role, content, html }) {
  hideWelcome();
  const wrap = document.createElement("div");
  wrap.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = avatarFor(role);

  const body = document.createElement("div");
  body.className = "body";
  if (html != null) {
    body.innerHTML = html;
  } else if (role === "user") {
    body.textContent = content;
  } else {
    body.innerHTML = renderMarkdown(content);
  }
  wrap.appendChild(avatar);
  wrap.appendChild(body);
  els.chat.appendChild(wrap);
  els.chat.scrollTop = els.chat.scrollHeight;
  return wrap;
}

function appendToolCall({ name, args, result, isError }) {
  hideWelcome();
  const wrap = document.createElement("div");
  wrap.className = "message tool";
  wrap.innerHTML = `<div class="avatar">⚙</div>`;

  const body = document.createElement("div");
  body.className = "body";

  const details = document.createElement("details");
  details.className = "tool-call";

  const summary = document.createElement("summary");
  const argsPreview = typeof args === "string" ? args : JSON.stringify(args);
  summary.innerHTML = `
    <span class="tool-name">${escapeHtml(name)}</span>
    <span class="tool-args">${escapeHtml(argsPreview).slice(0, 240)}</span>
  `;
  details.appendChild(summary);

  const inner = document.createElement("div");
  inner.className = "tool-body";
  inner.innerHTML = `
    <div class="label">Arguments</div>
    <pre>${escapeHtml(typeof args === "string" ? args : JSON.stringify(args, null, 2))}</pre>
    <div class="label">Result${isError ? " (error)" : ""}</div>
    <pre>${escapeHtml(result || "")}</pre>
  `;
  details.appendChild(inner);
  body.appendChild(details);

  wrap.appendChild(body);
  els.chat.appendChild(wrap);
  els.chat.scrollTop = els.chat.scrollHeight;
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------
const BUDGET_FIELDS = [
  "max_total_cost_usd",
  "max_total_tokens",
  "max_input_tokens",
  "max_output_tokens",
  "max_reasoning_tokens",
  "max_tool_calls",
  "max_model_calls",
  "max_delegated_tasks",
  "max_session_turns",
];

function applyServerState(state) {
  State.serverState = state;
  const f = els.settingsForm;
  f.model.value = state.model || "";
  f.base_url.value = state.base_url || "";
  f.cwd.value = state.cwd || "";
  f.allow_shell.checked = !!state.allow_shell;
  f.allow_write.checked = !!state.allow_write;
  if (f.stream_model_responses) f.stream_model_responses.checked = !!state.stream_model_responses;
  if (f.temperature) f.temperature.value = state.temperature ?? 0;
  if (f.timeout_seconds) f.timeout_seconds.value = state.timeout_seconds ?? 120;
  if (f.max_turns) f.max_turns.value = state.max_turns ?? 12;
  for (const name of BUDGET_FIELDS) {
    if (f[name]) f[name].value = state[name] == null ? "" : state[name];
  }
  for (const name of ["custom_system_prompt", "append_system_prompt", "override_system_prompt"]) {
    if (f[name]) f[name].value = state[name] || "";
  }
  if (f.response_schema) {
    f.response_schema.value = state.response_schema
      ? JSON.stringify(state.response_schema, null, 2)
      : "";
  }
  if (f.response_schema_name) f.response_schema_name.value = state.response_schema_name || "response";
  if (f.response_schema_strict) f.response_schema_strict.checked = !!state.response_schema_strict;
  if (f.auto_snip_threshold_tokens)
    f.auto_snip_threshold_tokens.value = state.auto_snip_threshold_tokens == null ? "" : state.auto_snip_threshold_tokens;
  if (f.auto_compact_threshold_tokens)
    f.auto_compact_threshold_tokens.value = state.auto_compact_threshold_tokens == null ? "" : state.auto_compact_threshold_tokens;
  if (f.compact_preserve_messages)
    f.compact_preserve_messages.value = state.compact_preserve_messages ?? 4;
  if (f.disable_claude_md_discovery)
    f.disable_claude_md_discovery.checked = !!state.disable_claude_md_discovery;
  if (f.additional_working_directories)
    f.additional_working_directories.value = (state.additional_working_directories || []).join("\n");
  els.cwdMeta.textContent = `cwd: ${state.cwd || "?"}`;
}

async function loadServerState() {
  try {
    const state = await apiGet("/api/state");
    applyServerState(state);
  } catch (e) {
    setStatus("error", `state: ${e.message}`);
  }
}

async function saveSettings(ev) {
  ev.preventDefault();
  const fd = new FormData(els.settingsForm);
  const f = els.settingsForm;
  const payload = {
    model: fd.get("model") || "",
    base_url: fd.get("base_url") || "",
    cwd: fd.get("cwd") || "",
    allow_shell: f.allow_shell.checked,
    allow_write: f.allow_write.checked,
  };
  if (f.stream_model_responses) payload.stream_model_responses = f.stream_model_responses.checked;
  const temp = fd.get("temperature");
  if (temp !== null && temp !== "") payload.temperature = Number(temp);
  const to = fd.get("timeout_seconds");
  if (to !== null && to !== "") payload.timeout_seconds = Number(to);
  const mt = fd.get("max_turns");
  if (mt !== null && mt !== "") payload.max_turns = Number(mt);
  // Budget knobs: empty string -> null (clear), numeric -> number.  Always
  // include them so "I just cleared the limit" round-trips to the server.
  for (const name of BUDGET_FIELDS) {
    if (!f[name]) continue;
    const raw = fd.get(name);
    payload[name] = raw === null || raw === "" ? null : Number(raw);
  }
  for (const name of ["custom_system_prompt", "append_system_prompt", "override_system_prompt"]) {
    if (!f[name]) continue;
    const raw = fd.get(name);
    payload[name] = raw && raw.trim() ? raw : null;
  }
  if (f.response_schema) {
    const raw = (fd.get("response_schema") || "").trim();
    if (!raw) {
      payload.response_schema = null;
    } else {
      try {
        payload.response_schema = JSON.parse(raw);
      } catch (parseErr) {
        setStatus("error", `schema: invalid JSON (${parseErr.message})`);
        return;
      }
    }
  }
  if (f.response_schema_name) {
    const raw = (fd.get("response_schema_name") || "").trim();
    if (raw) payload.response_schema_name = raw;
  }
  if (f.response_schema_strict) payload.response_schema_strict = f.response_schema_strict.checked;
  // Context-management knobs.
  for (const name of ["auto_snip_threshold_tokens", "auto_compact_threshold_tokens"]) {
    if (!f[name]) continue;
    const raw = fd.get(name);
    payload[name] = raw === null || raw === "" ? null : Number(raw);
  }
  if (f.compact_preserve_messages) {
    const raw = fd.get("compact_preserve_messages");
    if (raw !== null && raw !== "") payload.compact_preserve_messages = Number(raw);
  }
  if (f.disable_claude_md_discovery)
    payload.disable_claude_md_discovery = f.disable_claude_md_discovery.checked;
  if (f.additional_working_directories) {
    const raw = (fd.get("additional_working_directories") || "").trim();
    payload.additional_working_directories = raw
      ? raw.split(/\r?\n/).map((s) => s.trim()).filter(Boolean)
      : [];
  }
  try {
    setStatus("busy", "Saving settings…");
    const state = await apiPost("/api/state", payload);
    applyServerState(state);
    setStatus("ready", "Settings saved");
  } catch (e) {
    setStatus("error", `save: ${e.message}`);
  }
}

// ---------------------------------------------------------------------------
// Sessions
// ---------------------------------------------------------------------------
async function loadSessions() {
  try {
    const sessions = await apiGet("/api/sessions");
    State.sessions = sessions;
    renderSessions();
  } catch (e) {
    els.sessionList.innerHTML = `<div class="empty-state">${escapeHtml(e.message)}</div>`;
  }
}

function renderSessions() {
  els.sessionList.innerHTML = "";
  if (!State.sessions.length) {
    els.sessionList.innerHTML = `<div class="empty-state">No saved sessions yet.</div>`;
    return;
  }
  for (const s of State.sessions) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "session-item";
    if (s.session_id === State.activeSessionId) item.classList.add("active");
    const preview = s.preview || "(no preview)";
    item.innerHTML = `
      <div class="session-preview">${escapeHtml(preview)}</div>
      <div class="session-meta">${s.turns} turns · ${s.tool_calls} tools</div>
    `;
    item.addEventListener("click", () => openSession(s.session_id));
    els.sessionList.appendChild(item);
  }
}

async function openSession(sessionId) {
  try {
    setStatus("busy", "Loading session…");
    const session = await apiGet(`/api/sessions/${encodeURIComponent(sessionId)}`);
    State.activeSessionId = sessionId;
    clearChat();
    for (const msg of session.messages) {
      renderTranscriptEntry(msg);
    }
    renderSessions();
    setStatus("ready", `Session ${sessionId.slice(0, 8)}…`);
  } catch (e) {
    setStatus("error", `session: ${e.message}`);
  }
}

function newSession() {
  State.activeSessionId = null;
  clearChat();
  clearPasteStash();
  renderSessions();
  setStatus("ready", "New chat");
  els.input.focus();
}

// ---------------------------------------------------------------------------
// Transcript rendering
// ---------------------------------------------------------------------------
function renderTranscriptEntry(entry) {
  if (!entry || !entry.role) return;
  if (entry.role === "system") return;
  if (entry.role === "user") {
    appendMessage({ role: "user", content: entry.content || "" });
    return;
  }
  if (entry.role === "assistant") {
    if (entry.content && entry.content.trim()) {
      appendMessage({ role: "assistant", content: entry.content });
    }
    if (Array.isArray(entry.tool_calls)) {
      for (const tc of entry.tool_calls) {
        const name = tc?.function?.name || tc?.name || "tool";
        let args = tc?.function?.arguments ?? tc?.arguments ?? "";
        try {
          if (typeof args === "string") args = JSON.parse(args);
        } catch {}
        appendToolCall({ name, args, result: "(pending — see following tool message)" });
      }
    }
    return;
  }
  if (entry.role === "tool") {
    const name = entry.name || "tool";
    const meta = entry.metadata || {};
    appendToolCall({
      name,
      args: meta.action || "",
      result: entry.content || "",
      isError: meta.ok === false,
    });
    return;
  }
}

// ---------------------------------------------------------------------------
// Slash commands / skills palette
// ---------------------------------------------------------------------------
async function loadSlashCommands() {
  try {
    State.slashCommands = await apiGet("/api/slash-commands");
  } catch (e) {
    State.slashCommands = [];
  }
}

async function loadSkills() {
  try {
    State.skills = await apiGet("/api/skills");
  } catch (e) {
    State.skills = [];
  }
}

function openPalette(mode) {
  State.paletteMode = mode;
  els.palette.classList.remove("hidden");
  els.paletteSearch.value = "";
  renderPalette("");
  els.paletteSearch.focus();
}

function closePalette() {
  els.palette.classList.add("hidden");
  State.paletteMode = null;
}

function renderPalette(filter) {
  const items = State.paletteMode === "skills" ? State.skills : State.slashCommands;
  const f = (filter || "").toLowerCase().trim();
  els.paletteList.innerHTML = "";
  for (const item of items) {
    const display =
      State.paletteMode === "skills"
        ? { name: item.name, desc: item.description }
        : { name: `/${item.primary}`, desc: item.description };
    if (f && !display.name.toLowerCase().includes(f) && !display.desc.toLowerCase().includes(f))
      continue;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "palette-item";
    btn.innerHTML = `<span class="palette-name">${escapeHtml(display.name)}</span><span class="palette-desc">${escapeHtml(display.desc || "")}</span>`;
    btn.addEventListener("click", () => {
      if (State.paletteMode === "skills") {
        els.input.value = `Use the ${item.name} skill`;
      } else {
        els.input.value = `/${item.primary} `;
      }
      closePalette();
      autoSizeInput();
      els.input.focus();
    });
    els.paletteList.appendChild(btn);
  }
  if (!els.paletteList.children.length) {
    els.paletteList.innerHTML = `<div class="empty-state" style="padding:10px;">No matches.</div>`;
  }
}

// ---------------------------------------------------------------------------
// Paste-ref handling
// ---------------------------------------------------------------------------
function countNewlines(text) {
  // Match npm's getPastedTextRefNumLines: count of \r\n / \r / \n.
  const m = text.match(/\r\n|\r|\n/g);
  return m ? m.length : 0;
}

function formatPastedRef(id, lines) {
  return lines === 0 ? `[Pasted text #${id}]` : `[Pasted text #${id} +${lines} lines]`;
}

function renderPasteChips() {
  els.pasteChips.innerHTML = "";
  const ids = Object.keys(State.pastedContents)
    .map(Number)
    .sort((a, b) => a - b);
  if (!ids.length) {
    els.pasteChips.hidden = true;
    return;
  }
  els.pasteChips.hidden = false;
  for (const id of ids) {
    const entry = State.pastedContents[id];
    const chip = document.createElement("span");
    chip.className = "paste-chip";
    chip.innerHTML = `
      <span class="paste-chip-label">[Pasted text #${id}]</span>
      <span class="paste-chip-meta">${entry.lines} line${entry.lines === 1 ? "" : "s"} · ${entry.content.length} chars</span>
      <button type="button" class="paste-chip-remove" title="Remove">✕</button>
    `;
    chip.querySelector(".paste-chip-remove").addEventListener("click", () => {
      // Drop both the stash entry and any inline ref so a later send can't
      // refer to a paste the server doesn't have.
      delete State.pastedContents[id];
      const ref = formatPastedRef(id, entry.lines);
      els.input.value = els.input.value.split(ref).join("");
      autoSizeInput();
      renderPasteChips();
      els.input.focus();
    });
    els.pasteChips.appendChild(chip);
  }
}

function clearPasteStash() {
  State.pastedContents = {};
  State.nextPasteId = 1;
  renderPasteChips();
}

function handlePaste(ev) {
  const cd = ev.clipboardData;
  if (!cd) return;
  const text = cd.getData("text/plain");
  if (!text || text.length < PASTE_COLLAPSE_THRESHOLD) return;
  ev.preventDefault();

  const id = State.nextPasteId++;
  const lines = countNewlines(text);
  State.pastedContents[id] = { type: "text", content: text, lines };
  const ref = formatPastedRef(id, lines);

  // Splice at the current selection so the placeholder lands where the user
  // pasted, just like a normal paste would.
  const ta = els.input;
  const start = ta.selectionStart ?? ta.value.length;
  const end = ta.selectionEnd ?? ta.value.length;
  ta.value = ta.value.slice(0, start) + ref + ta.value.slice(end);
  const caret = start + ref.length;
  ta.setSelectionRange(caret, caret);

  autoSizeInput();
  renderPasteChips();
}

// ---------------------------------------------------------------------------
// Composer
// ---------------------------------------------------------------------------
function autoSizeInput() {
  els.input.style.height = "auto";
  els.input.style.height = Math.min(els.input.scrollHeight, 200) + "px";
}

async function send() {
  if (State.isBusy) return;
  const prompt = els.input.value.trim();
  if (!prompt) return;
  appendMessage({ role: "user", content: prompt });
  els.input.value = "";
  autoSizeInput();
  setBusy(true);
  try {
    const pastedContents = {};
    for (const [id, entry] of Object.entries(State.pastedContents)) {
      pastedContents[id] = { type: entry.type, content: entry.content };
    }
    const payload = {
      prompt,
      resume_session_id: State.activeSessionId || null,
      pasted_contents: pastedContents,
    };
    const data = await apiPost("/api/chat", payload);
    if (data.error) {
      appendMessage({ role: "error", content: `${data.error_type}: ${data.error}` });
      setStatus("error", "Error");
    } else {
      // Render tool calls + final response from the transcript so the user
      // sees what the agent actually did, not just the final reply.
      renderRunResult(data);
      State.activeSessionId = data.session_id || State.activeSessionId;
      els.usageMeta.textContent =
        `turns: ${data.turns}  ·  tools: ${data.tool_calls}` +
        (data.usage?.total_tokens
          ? `  ·  tokens: ${data.usage.total_tokens}`
          : "");
      clearPasteStash();
      await loadSessions();
    }
  } catch (e) {
    appendMessage({ role: "error", content: e.message });
    setStatus("error", "Error");
  } finally {
    setBusy(false);
    els.input.focus();
  }
}

function renderRunResult(data) {
  // We already rendered the user prompt. The transcript starts with system +
  // user + assistant turns; we want to show: any tool messages that happened
  // since the last user message, then the final assistant response.
  const transcript = data.transcript || [];
  let lastUserIndex = -1;
  for (let i = transcript.length - 1; i >= 0; i--) {
    if (transcript[i].role === "user") {
      lastUserIndex = i;
      break;
    }
  }
  const tail = transcript.slice(lastUserIndex + 1);
  for (const entry of tail) {
    if (entry.role === "assistant") {
      // Only render if it has visible content; tool_calls already rendered.
      if (Array.isArray(entry.tool_calls) && entry.tool_calls.length) {
        // Skip — corresponding tool messages will follow.
        continue;
      }
    }
    renderTranscriptEntry(entry);
  }
  // Always show the canonical final output if it isn't already present.
  const lastMsg = els.chat.querySelector(".message.assistant:last-of-type .body");
  if (!lastMsg || lastMsg.textContent.trim() !== (data.final_output || "").trim()) {
    if (data.final_output && data.final_output.trim()) {
      appendMessage({ role: "assistant", content: data.final_output });
    }
  }
}

// ---------------------------------------------------------------------------
// Tasks view
// ---------------------------------------------------------------------------
function renderTasks(payload) {
  const tasks = payload.tasks || [];
  els.tasksCounts.innerHTML = "";
  const counts = payload.counts || {};
  for (const status of ["pending", "in_progress", "blocked", "completed", "cancelled"]) {
    const n = counts[status] || 0;
    if (!n) continue;
    const chip = document.createElement("span");
    chip.className = "tasks-count-chip";
    chip.innerHTML = `<strong>${n}</strong>${status.replace("_", " ")}`;
    els.tasksCounts.appendChild(chip);
  }

  els.tasksList.innerHTML = "";
  if (!tasks.length) {
    els.tasksList.innerHTML = `<div class="empty-state">No tasks yet — add one above.</div>`;
    return;
  }
  for (const task of tasks) {
    const card = document.createElement("div");
    card.className = `task-card status-${task.status}`;
    if (task.is_next_actionable) card.classList.add("is-actionable");

    const status = document.createElement("span");
    status.className = `task-status status-${task.status}`;
    status.textContent = task.status;

    const body = document.createElement("div");
    body.className = "task-body";
    const title = document.createElement("div");
    title.className = "task-title";
    title.textContent = task.title;
    body.appendChild(title);
    if (task.description) {
      const desc = document.createElement("div");
      desc.className = "task-meta";
      desc.textContent = task.description;
      body.appendChild(desc);
    }
    const meta = document.createElement("div");
    meta.className = "task-meta";
    const bits = [`id ${task.task_id}`];
    if (task.priority) bits.push(`priority ${task.priority}`);
    if (task.owner) bits.push(`owner ${task.owner}`);
    if (task.blocked_by && task.blocked_by.length)
      bits.push(`blocked by ${task.blocked_by.join(", ")}`);
    if (task.metadata && task.metadata.cancel_reason)
      bits.push(`reason: ${task.metadata.cancel_reason}`);
    meta.textContent = bits.join(" · ");
    body.appendChild(meta);

    const actions = document.createElement("div");
    actions.className = "task-actions";
    if (task.status === "pending") {
      const start = document.createElement("button");
      start.textContent = "Start";
      start.addEventListener("click", () => taskAction(task.task_id, "start"));
      actions.appendChild(start);
    }
    if (task.status !== "completed" && task.status !== "cancelled") {
      const done = document.createElement("button");
      done.textContent = "Done";
      done.addEventListener("click", () => taskAction(task.task_id, "complete"));
      actions.appendChild(done);

      const cancel = document.createElement("button");
      cancel.textContent = "Cancel";
      cancel.addEventListener("click", async () => {
        const reason = prompt("Cancel reason (optional)") || null;
        await taskAction(task.task_id, "cancel", { reason });
      });
      actions.appendChild(cancel);
    }
    card.appendChild(status);
    card.appendChild(body);
    card.appendChild(actions);
    els.tasksList.appendChild(card);
  }
}

async function loadTasks() {
  try {
    const payload = await apiGet("/api/tasks");
    renderTasks(payload);
  } catch (e) {
    els.tasksList.innerHTML = `<div class="empty-state">${escapeHtml(e.message)}</div>`;
  }
}

async function taskAction(id, action, body) {
  try {
    const payload = await apiPost(`/api/tasks/${encodeURIComponent(id)}/${action}`, body || {});
    if (payload.state) renderTasks(payload.state);
    else await loadTasks();
  } catch (e) {
    setStatus("error", `task: ${e.message}`);
  }
}

async function createTask(ev) {
  ev.preventDefault();
  const fd = new FormData(els.tasksCreate);
  const title = (fd.get("title") || "").trim();
  if (!title) return;
  const body = { title };
  const priority = (fd.get("priority") || "").trim();
  if (priority) body.priority = priority;
  try {
    const payload = await apiPost("/api/tasks", body);
    els.tasksCreate.reset();
    if (payload.state) renderTasks(payload.state);
    else await loadTasks();
  } catch (e) {
    setStatus("error", `task: ${e.message}`);
  }
}

function setView(view) {
  document.body.dataset.view = view;
  for (const tab of els.viewTabs) {
    tab.classList.toggle("active", tab.dataset.view === view);
  }
  if (view === "tasks") loadTasks();
  if (view === "plan") loadPlan();
  if (view === "memory") loadMemory();
  if (view === "history") loadHistory();
  if (view === "bg") loadBackgroundList();
  if (view === "worktree") loadWorktree();
  if (view === "skills") loadSkillsView();
}

// ---------------------------------------------------------------------------
// Skills view
// ---------------------------------------------------------------------------
async function loadSkillsView() {
  try {
    const include = els.skillsIncludeInternal.checked ? "true" : "false";
    const skills = await apiGet(`/api/skills?include_internal=${include}`);
    State.skills = skills;
    els.skillsGrid.innerHTML = "";
    if (!skills.length) {
      els.skillsGrid.innerHTML = `<div class="empty-state">No skills available.</div>`;
      return;
    }
    for (const skill of skills) {
      const card = document.createElement("div");
      card.className = "skill-card";
      if (!skill.user_invocable) card.classList.add("internal");
      card.innerHTML = `
        <span class="skill-name">${escapeHtml(skill.name)}</span>
        <span class="skill-desc">${escapeHtml(skill.description || "")}</span>
        ${skill.when_to_use ? `<span class="skill-when">When: ${escapeHtml(skill.when_to_use)}</span>` : ""}
        <div class="skill-meta">
          ${(skill.aliases || []).map((a) => `<span class="skill-meta-pill">alias: ${escapeHtml(a)}</span>`).join("")}
          ${(skill.allowed_tools || []).map((t) => `<span class="skill-meta-pill">tool: ${escapeHtml(t)}</span>`).join("")}
        </div>
        <div class="skill-actions">
          <button data-act="use">Use in chat</button>
          <button data-act="copy">Copy name</button>
        </div>
      `;
      card.querySelector('[data-act="use"]').addEventListener("click", () => {
        if (!skill.user_invocable) {
          setStatus("error", "Internal skills can't be invoked from the composer.");
          return;
        }
        setView("chat");
        els.input.value = `Use the ${skill.name} skill`;
        autoSizeInput();
        els.input.focus();
      });
      card.querySelector('[data-act="copy"]').addEventListener("click", () => {
        navigator.clipboard?.writeText(skill.name);
        setStatus("ready", `Copied ${skill.name}`);
      });
      els.skillsGrid.appendChild(card);
    }
  } catch (e) {
    setStatus("error", `skills: ${e.message}`);
  }
}

// ---------------------------------------------------------------------------
// Worktree view
// ---------------------------------------------------------------------------
function renderWorktree(payload) {
  const status = payload.status || {};
  els.worktreeStatus.classList.toggle("active", !!status.active);
  const lines = [];
  const push = (label, value) => {
    if (value !== null && value !== undefined && value !== "")
      lines.push(`<span class="label">${label}</span><span class="value">${escapeHtml(String(value))}</span>`);
  };
  push("active", status.active ? "yes" : "no");
  push("detail", status.detail);
  push("repo_root", status.repo_root);
  push("current_cwd", status.current_cwd);
  push("worktree_path", status.worktree_path);
  push("worktree_branch", status.worktree_branch);
  push("session_name", status.session_name);
  push("history_count", status.history_count);
  els.worktreeStatus.innerHTML = lines.join("\n");
  els.worktreeExit.disabled = !status.active;

  els.worktreeHistory.innerHTML = "";
  if (!payload.history.length) {
    els.worktreeHistory.innerHTML = `<div class="empty-state">No worktree history yet.</div>`;
  } else {
    for (const entry of [...payload.history].reverse()) {
      const row = document.createElement("div");
      row.className = "history-row";
      const when = entry.timestamp
        ? new Date(entry.timestamp).toLocaleString()
        : "unknown";
      row.innerHTML = `
        <span class="history-when">${escapeHtml(when)}</span>
        <span class="history-tool">${escapeHtml(entry.action || "?")}</span>
        <span class="history-detail">${escapeHtml(entry.worktree_path || "")}</span>
        <span class="history-session">${escapeHtml(entry.name || "")}</span>
      `;
      els.worktreeHistory.appendChild(row);
    }
  }
}

async function loadWorktree() {
  try {
    renderWorktree(await apiGet("/api/worktree"));
  } catch (e) {
    setStatus("error", `worktree: ${e.message}`);
  }
}

async function enterWorktree(ev) {
  ev.preventDefault();
  const fd = new FormData(els.worktreeEnterForm);
  const name = (fd.get("name") || "").trim() || null;
  try {
    setStatus("busy", "Creating worktree…");
    const data = await apiPost("/api/worktree/enter", { name });
    renderWorktree(data);
    els.worktreeEnterForm.reset();
    setStatus("ready", "Entered worktree");
    // The agent's cwd just changed under us — refresh state snapshot so the
    // settings panel and chat footer reflect it.
    await loadServerState();
  } catch (e) {
    setStatus("error", `worktree: ${e.message}`);
  }
}

async function exitWorktree() {
  if (!confirm("Exit the active worktree?")) return;
  try {
    setStatus("busy", "Exiting worktree…");
    const data = await apiPost("/api/worktree/exit", {
      action: els.worktreeExitAction.value,
      discard_changes: !!els.worktreeDiscard.checked,
    });
    renderWorktree(data);
    setStatus("ready", "Exited worktree");
    await loadServerState();
  } catch (e) {
    setStatus("error", `worktree: ${e.message}`);
  }
}

// ---------------------------------------------------------------------------
// Background sessions view
// ---------------------------------------------------------------------------
function renderBgList(payload) {
  const counts = payload.counts || {};
  els.bgCounts.innerHTML = "";
  for (const status of ["running", "exited", "completed", "failed"]) {
    const n = counts[status] || 0;
    if (!n) continue;
    const chip = document.createElement("span");
    chip.className = "tasks-count-chip";
    chip.innerHTML = `<strong>${n}</strong>${status}`;
    els.bgCounts.appendChild(chip);
  }
  els.bgList.innerHTML = "";
  if (!payload.sessions.length) {
    els.bgList.innerHTML = `<div class="empty-state">No background sessions yet.<br/>Launch one with <code>agent-bg</code>.</div>`;
    return;
  }
  for (const sess of payload.sessions) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "memory-item";
    if (BgState.current === sess.background_id) btn.classList.add("active");
    btn.innerHTML = `
      <span class="memory-item-name">${escapeHtml(sess.background_id)} · ${escapeHtml(sess.status)}</span>
      <span class="memory-item-path">${escapeHtml((sess.prompt || "(no prompt)").slice(0, 80))}</span>
    `;
    btn.addEventListener("click", () => openBackground(sess.background_id));
    els.bgList.appendChild(btn);
  }
}

async function loadBackgroundList() {
  try {
    renderBgList(await apiGet("/api/background"));
  } catch (e) {
    setStatus("error", `bg: ${e.message}`);
  }
}

async function openBackground(id) {
  BgState.current = id;
  try {
    const detail = await apiGet(`/api/background/${encodeURIComponent(id)}`);
    BgState.status = detail.status;
    els.bgCurrent.textContent = id;
    const bits = [`status ${detail.status}`, `pid ${detail.pid}`, `model ${detail.model}`];
    if (detail.exit_code != null) bits.push(`exit ${detail.exit_code}`);
    if (detail.session_id) bits.push(`session ${detail.session_id.slice(0, 12)}`);
    els.bgFlags.textContent = bits.join(" · ");
    els.bgKill.disabled = detail.status !== "running";
    els.bgLogsRefresh.disabled = false;
    els.bgLogs.disabled = false;
    await loadBackgroundLogs();
    await loadBackgroundList();
  } catch (e) {
    setStatus("error", `bg: ${e.message}`);
  }
}

async function loadBackgroundLogs() {
  if (!BgState.current) return;
  try {
    const data = await apiGet(`/api/background/${encodeURIComponent(BgState.current)}/logs`);
    els.bgLogs.value = data.content || "";
    els.bgLogs.scrollTop = els.bgLogs.scrollHeight;
  } catch (e) {
    setStatus("error", `bg logs: ${e.message}`);
  }
}

async function killBackground() {
  if (!BgState.current) return;
  if (!confirm(`Kill background session ${BgState.current}?`)) return;
  try {
    await apiPost(`/api/background/${encodeURIComponent(BgState.current)}/kill`, {});
    setStatus("ready", "Killed");
    await openBackground(BgState.current);
  } catch (e) {
    setStatus("error", `bg: ${e.message}`);
  }
}

// ---------------------------------------------------------------------------
// File-history view
// ---------------------------------------------------------------------------
function describeHistoryEntry(entry) {
  if (entry.changed_paths && entry.changed_paths.length)
    return entry.changed_paths.join(", ");
  if (entry.command) return entry.command;
  if (entry.action) return entry.action;
  if (entry.result_preview) return entry.result_preview;
  return "(no detail)";
}

function renderHistory(payload) {
  els.historyMeta.textContent = `${payload.total} entr${payload.total === 1 ? "y" : "ies"} (showing ${payload.returned})`;
  els.historyList.innerHTML = "";
  if (!payload.entries.length) {
    els.historyList.innerHTML = `<div class="empty-state">No file history yet — make some edits via chat.</div>`;
    return;
  }
  for (const entry of payload.entries) {
    const row = document.createElement("div");
    const kind = entry.history_kind || entry.action || "other";
    row.className = `history-row kind-${kind}`;
    if (entry.ok === false) row.classList.add("error");
    const when = entry.timestamp
      ? new Date(entry.timestamp).toLocaleString()
      : "unknown time";
    row.innerHTML = `
      <span class="history-when">${escapeHtml(when)}</span>
      <span class="history-tool">${escapeHtml(entry.tool_name || kind)}</span>
      <span class="history-detail">${escapeHtml(describeHistoryEntry(entry))}</span>
      <span class="history-session">${escapeHtml((entry.session_id || "").slice(0, 12))}</span>
    `;
    els.historyList.appendChild(row);
  }
}

async function loadHistory() {
  try {
    const data = await apiGet("/api/file-history?limit=200");
    renderHistory(data);
  } catch (e) {
    setStatus("error", `history: ${e.message}`);
  }
}

// ---------------------------------------------------------------------------
// Plan view
// ---------------------------------------------------------------------------
function makePlanRow(step, index) {
  const row = document.createElement("div");
  row.className = "plan-step-row";
  row.dataset.index = index;
  row.innerHTML = `
    <span class="plan-step-index">${index + 1}.</span>
    <input type="text" name="step" placeholder="Step description…" />
    <select name="status"></select>
    <input type="text" name="priority" placeholder="priority" />
    <button type="button" class="plan-step-remove" title="Remove">✕</button>
  `;
  const sel = row.querySelector('select[name="status"]');
  for (const s of PLAN_STATUSES) {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = s;
    sel.appendChild(opt);
  }
  row.querySelector('input[name="step"]').value = step.step || "";
  row.querySelector('select[name="status"]').value = step.status || "pending";
  row.querySelector('input[name="priority"]').value = step.priority || "";
  row.querySelector(".plan-step-remove").addEventListener("click", () => {
    row.remove();
    renumberPlanRows();
  });
  return row;
}

function renumberPlanRows() {
  const rows = els.planSteps.querySelectorAll(".plan-step-row");
  rows.forEach((row, i) => {
    row.dataset.index = i;
    row.querySelector(".plan-step-index").textContent = `${i + 1}.`;
  });
}

function renderPlan(payload) {
  els.planExplanation.value = payload.explanation || "";
  els.planSteps.innerHTML = "";
  for (let i = 0; i < (payload.steps || []).length; i++) {
    els.planSteps.appendChild(makePlanRow(payload.steps[i], i));
  }
  if (!els.planSteps.children.length) {
    els.planSteps.appendChild(makePlanRow({}, 0));
  }
  els.planMeta.textContent = payload.updated_at
    ? `updated ${new Date(payload.updated_at).toLocaleString()}`
    : "no plan saved yet";
}

async function loadPlan() {
  try {
    renderPlan(await apiGet("/api/plan"));
  } catch (e) {
    setStatus("error", `plan: ${e.message}`);
  }
}

function collectPlan() {
  const rows = els.planSteps.querySelectorAll(".plan-step-row");
  const steps = [];
  for (const row of rows) {
    const step = (row.querySelector('input[name="step"]').value || "").trim();
    if (!step) continue;
    const entry = {
      step,
      status: row.querySelector('select[name="status"]').value || "pending",
    };
    const priority = (row.querySelector('input[name="priority"]').value || "").trim();
    if (priority) entry.priority = priority;
    steps.push(entry);
  }
  return {
    steps,
    explanation: (els.planExplanation.value || "").trim() || null,
    sync_tasks: !!els.planSyncTasks.checked,
  };
}

async function savePlan() {
  try {
    setStatus("busy", "Saving plan…");
    // Plan replace is a PUT, so we go around the apiPost helper.
    const r = await fetch("/api/plan", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectPlan()),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      setStatus("error", data.detail || `${r.status} ${r.statusText}`);
      return;
    }
    renderPlan(data);
    setStatus("ready", "Plan saved");
    if (els.planSyncTasks.checked) await loadTasks();
  } catch (e) {
    setStatus("error", `plan: ${e.message}`);
  }
}

// ---------------------------------------------------------------------------
// Memory view
// ---------------------------------------------------------------------------
function renderMemoryList(payload) {
  els.memoryList.innerHTML = "";
  if (!payload.files.length) {
    els.memoryList.innerHTML = `<div class="empty-state">No CLAUDE.md / .claude/rules files discovered.</div>`;
    return;
  }
  for (const entry of payload.files) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "memory-item";
    if (MemoryState.current === entry.path) btn.classList.add("active");
    btn.innerHTML = `
      <span class="memory-item-name">${escapeHtml(entry.name)}${entry.writable ? "" : " (read-only)"}</span>
      <span class="memory-item-path">${escapeHtml(entry.path)}</span>
    `;
    btn.addEventListener("click", () => openMemoryFile(entry.path));
    els.memoryList.appendChild(btn);
  }
}

async function loadMemory() {
  try {
    const payload = await apiGet("/api/memory");
    renderMemoryList(payload);
  } catch (e) {
    setStatus("error", `memory: ${e.message}`);
  }
}

async function openMemoryFile(path) {
  try {
    const r = await fetch(`/api/memory/file?path=${encodeURIComponent(path)}`);
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      setStatus("error", data.detail || `${r.status} ${r.statusText}`);
      return;
    }
    MemoryState.current = data.path;
    MemoryState.writable = !!data.writable;
    MemoryState.dirty = false;
    els.memoryCurrent.textContent = data.path;
    els.memoryFlags.textContent = data.writable
      ? `${data.size} bytes`
      : `${data.size} bytes · read-only`;
    els.memoryContent.value = data.content || "";
    els.memoryContent.disabled = !data.writable;
    els.memorySave.disabled = !data.writable;
    els.memoryDelete.disabled = !data.writable;
    // Repaint list so the active row updates.
    await loadMemory();
  } catch (e) {
    setStatus("error", `memory: ${e.message}`);
  }
}

async function saveMemory() {
  if (!MemoryState.current || !MemoryState.writable) return;
  try {
    setStatus("busy", "Saving memory…");
    const r = await fetch("/api/memory/file", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: MemoryState.current, content: els.memoryContent.value }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      setStatus("error", data.detail || `${r.status} ${r.statusText}`);
      return;
    }
    MemoryState.dirty = false;
    setStatus("ready", "Memory saved");
    await loadMemory();
  } catch (e) {
    setStatus("error", `memory: ${e.message}`);
  }
}

async function deleteMemory() {
  if (!MemoryState.current || !MemoryState.writable) return;
  if (!confirm(`Delete ${MemoryState.current}?`)) return;
  try {
    const r = await fetch(
      `/api/memory/file?path=${encodeURIComponent(MemoryState.current)}`,
      { method: "DELETE" }
    );
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      setStatus("error", data.detail || `${r.status} ${r.statusText}`);
      return;
    }
    MemoryState.current = null;
    MemoryState.writable = false;
    els.memoryContent.value = "";
    els.memoryContent.disabled = true;
    els.memorySave.disabled = true;
    els.memoryDelete.disabled = true;
    els.memoryCurrent.textContent = "Pick a file to edit";
    els.memoryFlags.textContent = "";
    setStatus("ready", "Deleted");
    await loadMemory();
  } catch (e) {
    setStatus("error", `memory: ${e.message}`);
  }
}

async function newMemoryFile() {
  const suggested = "CLAUDE.local.md";
  const name = prompt("New memory file path (relative to cwd or absolute):", suggested);
  if (!name) return;
  // Use the cwd from the snapshot so the new file lands inside the workspace.
  const cwd = State.serverState?.cwd || "";
  const target = name.startsWith("/") || name.startsWith("~") ? name : `${cwd}/${name}`;
  try {
    const r = await fetch("/api/memory/file", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: target, content: "" }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      setStatus("error", data.detail || `${r.status} ${r.statusText}`);
      return;
    }
    await loadMemory();
    await openMemoryFile(data.path);
  } catch (e) {
    setStatus("error", `memory: ${e.message}`);
  }
}

async function clearPlan() {
  if (!confirm("Clear the entire plan?")) return;
  try {
    const data = await apiPost("/api/plan/clear", {
      sync_tasks: !!els.planSyncTasks.checked,
    });
    renderPlan(data);
    if (els.planSyncTasks.checked) await loadTasks();
    setStatus("ready", "Plan cleared");
  } catch (e) {
    setStatus("error", `plan: ${e.message}`);
  }
}

// ---------------------------------------------------------------------------
// Wire up
// ---------------------------------------------------------------------------
function bind() {
  els.input.addEventListener("input", autoSizeInput);
  els.input.addEventListener("paste", handlePaste);
  els.input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });
  els.sendBtn.addEventListener("click", send);
  els.newSessionBtn.addEventListener("click", newSession);
  els.settingsForm.addEventListener("submit", saveSettings);
  els.slashBtn.addEventListener("click", () => openPalette("slash"));
  els.skillsBtn.addEventListener("click", () => openPalette("skills"));
  els.clearBtn.addEventListener("click", async () => {
    try {
      setStatus("busy", "Clearing…");
      await apiPost("/api/clear", {});
      newSession();
      setStatus("ready", "Cleared");
    } catch (e) {
      setStatus("error", e.message);
    }
  });
  els.paletteClose.addEventListener("click", closePalette);
  els.palette.addEventListener("click", (e) => {
    if (e.target === els.palette) closePalette();
  });
  els.paletteSearch.addEventListener("input", (e) => renderPalette(e.target.value));
  for (const tab of els.viewTabs) {
    tab.addEventListener("click", () => setView(tab.dataset.view));
  }
  if (els.tasksCreate) els.tasksCreate.addEventListener("submit", createTask);
  if (els.tasksRefresh) els.tasksRefresh.addEventListener("click", loadTasks);
  if (els.planSave) els.planSave.addEventListener("click", savePlan);
  if (els.planClear) els.planClear.addEventListener("click", clearPlan);
  if (els.planRefresh) els.planRefresh.addEventListener("click", loadPlan);
  if (els.planAddStep) els.planAddStep.addEventListener("click", () => {
    const idx = els.planSteps.querySelectorAll(".plan-step-row").length;
    els.planSteps.appendChild(makePlanRow({}, idx));
  });
  if (els.memorySave) els.memorySave.addEventListener("click", saveMemory);
  if (els.memoryDelete) els.memoryDelete.addEventListener("click", deleteMemory);
  if (els.memoryRefresh) els.memoryRefresh.addEventListener("click", loadMemory);
  if (els.memoryNew) els.memoryNew.addEventListener("click", newMemoryFile);
  if (els.historyRefresh) els.historyRefresh.addEventListener("click", loadHistory);
  if (els.bgRefresh) els.bgRefresh.addEventListener("click", loadBackgroundList);
  if (els.bgKill) els.bgKill.addEventListener("click", killBackground);
  if (els.bgLogsRefresh) els.bgLogsRefresh.addEventListener("click", loadBackgroundLogs);
  if (els.worktreeRefresh) els.worktreeRefresh.addEventListener("click", loadWorktree);
  if (els.worktreeEnterForm) els.worktreeEnterForm.addEventListener("submit", enterWorktree);
  if (els.worktreeExit) els.worktreeExit.addEventListener("click", exitWorktree);
  if (els.skillsRefresh) els.skillsRefresh.addEventListener("click", loadSkillsView);
  if (els.skillsIncludeInternal)
    els.skillsIncludeInternal.addEventListener("change", loadSkillsView);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !els.palette.classList.contains("hidden")) {
      closePalette();
    }
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      openPalette("slash");
    }
  });
}

async function init() {
  bind();
  setView("chat");
  setStatus("ready", "Ready");
  await Promise.all([
    loadServerState(),
    loadSessions(),
    loadSlashCommands(),
    loadSkills(),
  ]);
  els.input.focus();
}

init();
