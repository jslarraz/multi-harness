from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .agents import AGENT_REGISTRY, AgentSpec
from .harness import AGENTS_MD, HARNESS_AGENTS, HARNESS_SKILLS

LinkStatus = Literal["ok", "missing", "broken", "detached"]


def check_symlink(link: Path, expected_target: Path) -> LinkStatus:
    if link.is_symlink():
        resolved = (link.parent / os.readlink(link)).resolve()
        return "ok" if resolved == expected_target.resolve() else "broken"
    if link.exists():
        return "detached"
    return "missing"


@dataclass
class AgentStatusRow:
    label: str
    status: LinkStatus


@dataclass
class AgentStatus:
    spec: AgentSpec
    rows: list[AgentStatusRow]

    def is_ok(self) -> bool:
        return all(r.status == "ok" for r in self.rows)


def check_agent(root: Path, spec: AgentSpec) -> AgentStatus:
    rows: list[AgentStatusRow] = []

    if spec.instructions_path is not None and spec.instructions_path != AGENTS_MD:
        rows.append(AgentStatusRow(
            label=str(spec.instructions_path),
            status=check_symlink(root / spec.instructions_path, root / AGENTS_MD),
        ))

    rows.append(AgentStatusRow(
        label=str(spec.skills_path),
        status=check_symlink(root / spec.skills_path, root / HARNESS_SKILLS),
    ))
    rows.append(AgentStatusRow(
        label=str(spec.subagents_path),
        status=check_symlink(root / spec.subagents_path, root / HARNESS_AGENTS),
    ))

    return AgentStatus(spec=spec, rows=rows)


def check_all(root: Path, agent_names: list[str]) -> list[AgentStatus]:
    return [check_agent(root, AGENT_REGISTRY[name]) for name in agent_names]
