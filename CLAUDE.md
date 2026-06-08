# multi-harness — project reference

## What this is

`mh` is a Python CLI that lets a single project share skills, subagents, and project
instructions across multiple coding agents without duplication. It creates a canonical
`.harness/` directory and materializes per-agent symlinks so every agent sees its
expected paths.

Console script: `mh` (installed via `pip install -e .`)
Package: `multi_harness` — `src/` layout, `pyproject.toml` + hatchling.

---

## Architecture

```
src/multi_harness/
├── cli.py          Typer app (group mode via @app.callback()).
│                   Entry point: mh init, future: mh add/remove/status/sync
├── harness.py      Core logic: detect_configured_agents(), init().
│                   Owns the HARNESS_DIR / AGENTS_MD path constants.
├── symlinks.py     ensure_symlink(link, target) — relative, idempotent, never
│                   overwrites real files. Returns "created"/"ok"/"replaced".
└── agents/
    ├── spec.py     AgentSpec dataclass (frozen). Fields: name, display_name,
    │               instructions_path (None if native AGENTS.md reader),
    │               skills_path, subagents_path, detection_paths.
    ├── __init__.py AGENT_REGISTRY: dict[str, AgentSpec] — add a new file here
    │               to support a new agent.
    ├── claude.py        Claude Code
    ├── codex.py         OpenAI Codex CLI
    ├── opencode.py      OpenCode
    ├── copilot.py       GitHub Copilot
    └── antigravity.py   Google Antigravity
```

Tests live in `tests/test_init.py`. Run with `.venv/bin/pytest`.

---

## Canonical layout produced by `mh init`

```
AGENTS.md               canonical project instructions (real file)
.harness/
  skills/               real dir — shared skills
  agents/               real dir — shared subagents
CLAUDE.md            -> AGENTS.md
.claude/
  skills               -> ../.harness/skills
  agents               -> ../.harness/agents
  settings.json           (untouched — agent-specific)
.codex/
  skills               -> ../.harness/skills
  agents               -> ../.harness/agents
.opencode/
  skills               -> ../.harness/skills
  agent                -> ../.harness/agents   (NB: singular)
.github/
  copilot-instructions.md -> ../AGENTS.md
  skills               -> ../.harness/skills
  agents               -> ../.harness/agents
.agents/
  skills               -> ../.harness/skills
.subagents             -> .harness/agents       (Antigravity — root-level)
```

All symlinks are **relative** so the tree is portable across machines and paths.

---

## Per-agent path reference (as of 2026)

| Agent | instructions_path | skills_path | subagents_path | detection_paths |
|-------|-------------------|-------------|----------------|-----------------|
| claude | `CLAUDE.md` | `.claude/skills` | `.claude/agents` | `CLAUDE.md`, `.claude` |
| codex | *native AGENTS.md* | `.codex/skills` | `.codex/agents` | `.codex` |
| opencode | *native AGENTS.md* | `.opencode/skills` | `.opencode/agent` ⚠️ | `.opencode` |
| copilot | `.github/copilot-instructions.md` | `.github/skills` | `.github/agents` | `.github/copilot-instructions.md` |
| antigravity | *native AGENTS.md* | `.agents/skills` | `.subagents` ⚠️ | `.agents`, `.subagents` |

⚠️ opencode uses singular `agent/` (not `agents/`).  
⚠️ Antigravity's subagent path `.subagents/` is root-level, inferred from docs as of Jun 2026 — may need revision.

**Adding a new agent:** create `src/multi_harness/agents/<name>.py` with a `SPEC`
`AgentSpec` instance, then add it to `AGENT_REGISTRY` in `agents/__init__.py`.

---

## Key design decisions

**Detection skips symlinks.** `detect_configured_agents()` only fires when
`.harness/` does NOT yet exist. On `--force` re-init, detection is skipped entirely
— we never mistake our own symlinks for a natively-configured agent.

**`AGENTS.md` is not a detection signal.** Three agents (codex, opencode, antigravity)
natively read `AGENTS.md`, so its presence is ambiguous. Detection looks only at
agent-specific dirs/files (`.codex/`, `.opencode/`, `.github/copilot-instructions.md`,
`.agents/`, `.subagents/`, `CLAUDE.md`, `.claude/`).

**`instructions_path=None` means the agent is an AGENTS.md native.** No instruction
symlink is created for codex/opencode/antigravity — they already find the canonical
file. Only `CLAUDE.md` and `.github/copilot-instructions.md` need symlinks.

**`ensure_symlink` never deletes user data.** If the link target already exists as a
real file or directory, it raises `HarnessError` and the whole `init()` call aborts.
Migration happens before symlink creation, so migrated dirs are real dirs in `.harness/`
by the time symlinks are created.

**Migration is one-shot.** When exactly one agent is detected, its files are moved into
`.harness/` and symlinks replace them. There is no "dry-run" or partial migration.

---

## Upcoming commands (planned)

All four commands will depend on a `.harness/config.toml` that records which agents are
registered for the project. `mh init` will write this file; subsequent commands read it.

### `mh add <agent> [--agents ...]`
Register one or more new agents to an existing harness: validate that `.harness/` exists,
create the symlinks for the new agent(s), update config.toml.

### `mh remove <agent> [--agents ...]`
Remove an agent's symlinks (unlink instructions, skills, subagents paths) without deleting
any `.harness/` content. Update config.toml.

### `mh status`
Read config.toml to know which agents are registered, then inspect each symlink:
- `ok` — symlink exists and points to the right place
- `missing` — symlink is absent (agent was added manually after init?)
- `broken` — symlink target doesn't resolve
- `detached` — real file/dir where a symlink should be
Report per-agent, per-link.

### `mh sync [--agents ...]`
Re-create any missing or broken symlinks for registered agents (like `--force` but
restricted to links that actually need repair). Reads config.toml, calls `ensure_symlink`
for each link, skips those that are already `"ok"`.

---

## config.toml schema (planned)

File: `.harness/config.toml`

```toml
[harness]
version = 1
agents = ["claude", "codex", "opencode", "copilot", "antigravity"]
```

The `agents` list is the source of truth for which agents are registered. Commands that
need it (`status`, `sync`, `add`, `remove`) read it; `init` writes it.

---

## Open questions / future considerations

- **Antigravity subagent path:** documented as `.subagents/` (root-level). Confirm when
  official Antigravity docs clarify the subagents directory convention.
- **config.toml location:** `.harness/config.toml` keeps all harness state in one place;
  an alternative is `multi-harness.toml` at the repo root (more visible).
- **Skill/agent file format validation:** should `mh` inspect SKILL.md frontmatter (name,
  description fields) for correctness? Deferred for now.
- **Per-agent instruction overlays** (`.harness/instructions/<agent>.md`) are explicitly
  out of scope for now — one shared AGENTS.md is the intent.

---

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest             # 13 tests, all scenarios
.venv/bin/mh --help
.venv/bin/mh init --help
```
