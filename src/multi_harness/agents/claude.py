from pathlib import Path

from .spec import AgentSpec

SPEC = AgentSpec(
    name="claude",
    display_name="Claude Code",
    instructions_path=Path("CLAUDE.md"),
    skills_path=Path(".claude/skills"),
    subagents_path=Path(".claude/agents"),
    detection_paths=(Path("CLAUDE.md"), Path(".claude")),
)
