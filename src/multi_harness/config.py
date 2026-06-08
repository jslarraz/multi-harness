from __future__ import annotations

import tomllib
from pathlib import Path

_HARNESS_DIR = Path(".harness")
HARNESS_CONFIG = _HARNESS_DIR / "config.toml"


class ConfigError(Exception):
    """Raised when .harness/config.toml is absent or has unexpected structure."""


def write_config(root: Path, agent_names: list[str]) -> None:
    agents_repr = ", ".join(f'"{n}"' for n in agent_names)
    (root / HARNESS_CONFIG).write_text(
        f"[harness]\nversion = 1\nagents = [{agents_repr}]\n"
    )


def read_agent_names(root: Path) -> list[str]:
    config_path = root / HARNESS_CONFIG
    if not config_path.exists():
        raise ConfigError(
            f"{HARNESS_CONFIG} not found. Run `mh init` to register agents."
        )
    try:
        with config_path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{HARNESS_CONFIG} is malformed: {exc}") from exc

    try:
        agents = data["harness"]["agents"]
    except KeyError as exc:
        raise ConfigError(
            f"{HARNESS_CONFIG} is missing key {exc}. Re-run `mh init`."
        ) from exc

    if not isinstance(agents, list) or not all(isinstance(n, str) for n in agents):
        raise ConfigError(
            f"{HARNESS_CONFIG}: harness.agents must be a list of strings."
        )

    return agents
