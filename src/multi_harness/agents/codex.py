from pathlib import Path

from .spec import AgentSpec

SPEC = AgentSpec(
    name="codex",
    display_name="OpenAI Codex",
    instructions_path=None,
    skills_path=Path(".codex/skills"),
    subagents_path=Path(".codex/agents"),
    detection_paths=(Path(".codex"),),
)
