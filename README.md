# multi-harness

A CLI (`mh`) to manage projects that target multiple coding agents from a single
shared `.harness/` directory.

Supported agents: Claude Code, OpenAI Codex CLI, OpenCode, GitHub Copilot,
Google Antigravity.

## Install

```bash
pip install -e .
```

## Usage

```bash
mh init                                     # initialize for all five agents
mh init --agents claude,codex               # only register two
mh init --template ./AGENTS_TEMPLATE.md     # seed AGENTS.md from a template
mh init --force                             # re-link symlinks idempotently
```

`mh init` either bootstraps an empty project or migrates a project that already
has exactly one agent configured into the shared `.harness/` layout, then
materializes per-agent symlinks so each agent sees its expected paths.
