from pathlib import Path

from .spec import AgentSpec

SPEC = AgentSpec(
    name="opencode",
    display_name="OpenCode",
    instructions_path=None,
    skills_path=Path(".opencode/skills"),
    subagents_path=Path(".opencode/agent"),
    detection_paths=(Path(".opencode"),),
)
