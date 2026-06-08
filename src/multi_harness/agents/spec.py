from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentSpec:
    name: str
    display_name: str
    instructions_path: Path | None
    skills_path: Path
    subagents_path: Path
    detection_paths: tuple[Path, ...]
