# multi-harness 🔗

> One project. Many coding agents. Zero duplication.

`mh` is a CLI that keeps your skills, subagents, and project instructions in a single
canonical `.harness/` directory and materialises per-agent symlinks so every agent sees
the paths it expects — no copy-paste, no drift.

**Supported agents:** Claude Code · OpenAI Codex CLI · OpenCode · GitHub Copilot · Google Antigravity

---

## ✨ Why multi-harness?

Each coding agent looks for instructions, skills, and subagents in different places:
`CLAUDE.md`, `.github/copilot-instructions.md`, `AGENTS.md`, `.claude/skills/`, `.codex/skills/` …

Without `mh` you either duplicate these files across every agent-specific location or
keep them in sync by hand. `mh` solves this by:

1. Creating one real `.harness/` directory with the canonical files.
2. Writing relative symlinks everywhere each agent expects to look.
3. Detecting an existing single-agent project and **migrating** it automatically.

---

## 📦 Installation

```bash
pip install multi-harness
```

Verify the install:

```bash
mh --help
```

---

## 🚀 Quick start

```bash
cd my-project
mh init
```

That's it. `mh` detects which agents are already configured, migrates their files into
`.harness/`, and creates symlinks for all five supported agents.

---

## 📖 Commands

### `mh init` — bootstrap or migrate a project

```bash
mh init                                      # all five agents, current directory
mh init --agents claude,codex                # register only two agents
mh init --template ./AGENTS_TEMPLATE.md      # seed AGENTS.md from a template file
mh init --force                              # re-create symlinks idempotently (safe)
mh init /path/to/project                     # target a different directory
```

On first run `mh init`:
- Creates `AGENTS.md` (or uses your `--template`) as the shared project instructions file.
- Creates `.harness/skills/` and `.harness/agents/` as the shared canonical directories.
- Writes relative symlinks for every registered agent (see layout below).
- Records the registered agents in `.harness/config.toml`.

If exactly **one** agent is already configured, `mh init` migrates its files into
`.harness/` before creating symlinks — your existing work is preserved, not overwritten.

---

### `mh add` — register new agents

```bash
mh add copilot                               # add a single agent
mh add opencode antigravity                  # add multiple agents at once
```

Creates the symlinks for the new agent(s) and updates `.harness/config.toml`. Requires
`mh init` to have been run first.

---

### `mh remove` — unregister agents

```bash
mh remove codex                              # remove one agent
mh remove opencode copilot                   # remove several at once
```

Removes the agent's symlinks (instructions, skills, subagents) without touching any file
inside `.harness/`. Your shared content is never deleted.

---

### `mh status` — inspect symlink health

```bash
mh status                                    # check current directory
mh status /path/to/project                   # check another directory
```

Reports the state of every symlink for every registered agent:

| Status | Meaning |
|--------|---------|
| ✅ `ok` | Symlink exists and resolves correctly |
| ❌ `missing` | Symlink is absent |
| 💔 `broken` | Symlink exists but target doesn't resolve |
| ⚠️ `detached` | A real file/dir sits where a symlink should be |

---

## 🗂️ Layout produced by `mh init`

```
my-project/
├── AGENTS.md                          ← canonical shared instructions (real file)
├── CLAUDE.md                         → AGENTS.md
├── .harness/
│   ├── config.toml                    ← registered agents list
│   ├── skills/                        ← shared skills (real dir)
│   └── agents/                        ← shared subagents (real dir)
├── .claude/
│   ├── skills                        → ../.harness/skills
│   └── agents                        → ../.harness/agents
├── .codex/
│   ├── skills                        → ../.harness/skills
│   └── agents                        → ../.harness/agents
├── .opencode/
│   ├── skills                        → ../.harness/skills
│   └── agent                         → ../.harness/agents
├── .github/
│   ├── copilot-instructions.md       → ../AGENTS.md
│   ├── skills                        → ../.harness/skills
│   └── agents                        → ../.harness/agents
└── .agents/
    └── skills                        → ../.harness/skills
```

All symlinks are **relative**, so the tree is fully portable across machines and paths.

---

## 🔄 Typical workflow

```bash
# 1. Bootstrap a new project
mh init --agents claude,codex

# 2. Add an agent later
mh add copilot

# 3. Check everything is wired up correctly
mh status

# 4. Remove an agent you no longer use
mh remove antigravity
```

Write your instructions once in `AGENTS.md`, drop skills into `.harness/skills/`, and
place shared subagents in `.harness/agents/` — every registered agent picks them up
automatically.

---

## 🛡️ Safety guarantees

- **Symlinks never overwrite real files.** If a real file or directory already exists
  where a symlink should go, `mh` aborts with an error rather than deleting your data.
- **`--force` is safe.** It re-creates symlinks but still refuses to touch real files.
- **Migration is non-destructive.** Files are moved into `.harness/`; nothing is deleted.
