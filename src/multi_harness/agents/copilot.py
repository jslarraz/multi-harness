from pathlib import Path

from .spec import AgentSpec

SPEC = AgentSpec(
    name="copilot",
    display_name="GitHub Copilot",
    instructions_path=Path(".github/copilot-instructions.md"),
    skills_path=Path(".github/skills"),
    subagents_path=Path(".github/agents"),
    detection_paths=(Path(".github/copilot-instructions.md"),),
)
