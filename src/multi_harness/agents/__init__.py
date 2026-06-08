from .antigravity import SPEC as _ANTIGRAVITY
from .claude import SPEC as _CLAUDE
from .codex import SPEC as _CODEX
from .copilot import SPEC as _COPILOT
from .opencode import SPEC as _OPENCODE
from .spec import AgentSpec

AGENT_REGISTRY: dict[str, AgentSpec] = {
    spec.name: spec
    for spec in (_CLAUDE, _CODEX, _OPENCODE, _COPILOT, _ANTIGRAVITY)
}

__all__ = ["AGENT_REGISTRY", "AgentSpec"]
