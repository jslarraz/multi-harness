from pathlib import Path

from .spec import AgentSpec

SPEC = AgentSpec(
    name="antigravity",
    display_name="Google Antigravity",
    instructions_path=None,
    skills_path=Path(".agents/skills"),
    subagents_path=Path(".subagents"),
    detection_paths=(Path(".agents"), Path(".subagents")),
)
