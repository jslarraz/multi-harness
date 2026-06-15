from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .agents import AGENT_REGISTRY, AgentSpec
from .config import ConfigError, read_agent_names, write_config
from .symlinks import SymlinkResult, ensure_symlink

HARNESS_DIR = Path(".harness")
HARNESS_SKILLS = HARNESS_DIR / "skills"
HARNESS_AGENTS = HARNESS_DIR / "agents"
AGENTS_MD = Path("AGENTS.md")


class HarnessError(Exception):
    """Raised when `mh init` cannot safely proceed."""


@dataclass
class InitReport:
    detected: list[AgentSpec] = field(default_factory=list)
    moved: list[tuple[Path, Path]] = field(default_factory=list)
    created_files: list[Path] = field(default_factory=list)
    symlinks: list[tuple[Path, SymlinkResult]] = field(default_factory=list)


@dataclass
class AddReport:
    symlinks: list[tuple[Path, SymlinkResult]] = field(default_factory=list)


@dataclass
class RemoveReport:
    removed_symlinks: list[Path] = field(default_factory=list)
    removed_dirs: list[Path] = field(default_factory=list)
    nonempty_dirs: list[Path] = field(default_factory=list)


def detect_configured_agents(root: Path) -> list[AgentSpec]:
    """Return registered agents whose real detection paths exist under ``root``."""
    detected: list[AgentSpec] = []
    for spec in AGENT_REGISTRY.values():
        for p in spec.detection_paths:
            candidate = root / p
            if candidate.exists() and not candidate.is_symlink():
                detected.append(spec)
                break
    return detected


def _move(src: Path, dst: Path, report: InitReport) -> None:
    if dst.exists() or dst.is_symlink():
        raise HarnessError(
            f"Cannot migrate {src} -> {dst}: destination already exists. "
            f"Resolve the conflict and re-run."
        )
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)
    report.moved.append((src, dst))


def _migrate(root: Path, spec: AgentSpec, report: InitReport) -> None:
    if spec.instructions_path is not None:
        src = root / spec.instructions_path
        dst = root / AGENTS_MD
        if src.exists() and not src.is_symlink() and src != dst:
            _move(src, dst, report)

    src_skills = root / spec.skills_path
    if src_skills.is_dir() and not src_skills.is_symlink():
        _move(src_skills, root / HARNESS_SKILLS, report)

    src_subagents = root / spec.subagents_path
    if src_subagents.is_dir() and not src_subagents.is_symlink():
        _move(src_subagents, root / HARNESS_AGENTS, report)


def init(
    root: Path,
    agent_names: list[str],
    template: Path | None = None,
    force: bool = False,
) -> InitReport:
    """Initialize (or re-initialize) the harness layout at ``root``.

    Raises :class:`HarnessError` if the project is in a state that requires manual
    resolution (e.g. multiple agents already configured, or `.harness/` already
    exists without ``--force``).
    """
    unknown = [n for n in agent_names if n not in AGENT_REGISTRY]
    if unknown:
        raise HarnessError(
            f"Unknown agent(s): {', '.join(unknown)}. "
            f"Supported: {', '.join(AGENT_REGISTRY)}."
        )

    report = InitReport()
    harness_existed = (root / HARNESS_DIR).exists()

    if harness_existed and not force:
        raise HarnessError(
            f"{HARNESS_DIR}/ already exists. Pass --force to re-link symlinks idempotently."
        )

    if not harness_existed:
        report.detected = detect_configured_agents(root)
        if len(report.detected) > 1:
            names = ", ".join(s.display_name for s in report.detected)
            raise HarnessError(
                f"More than one agent is already configured ({names}). "
                f"Resolve manually (remove all but one) and re-run."
            )
        if len(report.detected) == 1:
            _migrate(root, report.detected[0], report)

    (root / HARNESS_SKILLS).mkdir(parents=True, exist_ok=True)
    (root / HARNESS_AGENTS).mkdir(parents=True, exist_ok=True)

    agents_md = root / AGENTS_MD
    if not agents_md.exists() and not agents_md.is_symlink():
        if template is not None:
            agents_md.write_text(template.read_text())
        else:
            agents_md.touch()
        report.created_files.append(agents_md)

    for name in agent_names:
        _create_agent_symlinks(root, AGENT_REGISTRY[name], report.symlinks)

    write_config(root, agent_names)
    return report


def _create_agent_symlinks(
    root: Path,
    spec: AgentSpec,
    out: list[tuple[Path, SymlinkResult]],
) -> None:
    if spec.instructions_path is not None and spec.instructions_path != AGENTS_MD:
        link = root / spec.instructions_path
        try:
            result = ensure_symlink(link, root / AGENTS_MD)
        except FileExistsError as exc:
            raise HarnessError(str(exc)) from exc
        out.append((link, result))
    for link_rel, target_rel in (
        (spec.skills_path, HARNESS_SKILLS),
        (spec.subagents_path, HARNESS_AGENTS),
    ):
        link = root / link_rel
        try:
            result = ensure_symlink(link, root / target_rel)
        except FileExistsError as exc:
            raise HarnessError(str(exc)) from exc
        out.append((link, result))


def add(root: Path, agent_names: list[str]) -> AddReport:
    """Register new agents to an already-initialized harness.

    Raises :class:`HarnessError` if the harness is absent, any name is unknown,
    or any agent is already registered.
    """
    unknown = [n for n in agent_names if n not in AGENT_REGISTRY]
    if unknown:
        raise HarnessError(
            f"Unknown agent(s): {', '.join(unknown)}. "
            f"Supported: {', '.join(AGENT_REGISTRY)}."
        )

    if not (root / HARNESS_DIR).exists():
        raise HarnessError(f"{HARNESS_DIR}/ not found. Run `mh init` first.")

    try:
        current = read_agent_names(root)
    except ConfigError as exc:
        raise HarnessError(str(exc)) from exc

    already = [n for n in agent_names if n in current]
    if already:
        raise HarnessError(
            f"Agent(s) already registered: {', '.join(already)}. "
            f"Run `mh remove` first if you want to re-add."
        )

    report = AddReport()
    for name in agent_names:
        _create_agent_symlinks(root, AGENT_REGISTRY[name], report.symlinks)

    write_config(root, current + agent_names)
    return report


def remove(root: Path, agent_names: list[str]) -> RemoveReport:
    """Unlink symlinks for the given agents and clean up empty parent directories.

    Raises :class:`HarnessError` if the harness is absent, any name is unknown,
    or any agent is not currently registered.

    Non-empty parent directories are reported in ``RemoveReport.nonempty_dirs``
    and left for the caller to handle (e.g. interactive prompt).
    """
    unknown = [n for n in agent_names if n not in AGENT_REGISTRY]
    if unknown:
        raise HarnessError(
            f"Unknown agent(s): {', '.join(unknown)}. "
            f"Supported: {', '.join(AGENT_REGISTRY)}."
        )

    if not (root / HARNESS_DIR).exists():
        raise HarnessError(f"{HARNESS_DIR}/ not found. Run `mh init` first.")

    try:
        current = read_agent_names(root)
    except ConfigError as exc:
        raise HarnessError(str(exc)) from exc

    not_registered = [n for n in agent_names if n not in current]
    if not_registered:
        raise HarnessError(
            f"Agent(s) not registered: {', '.join(not_registered)}. "
            f"Run `mh status` to see registered agents."
        )

    report = RemoveReport()
    parent_dirs: set[Path] = set()

    for name in agent_names:
        spec = AGENT_REGISTRY[name]
        links: list[Path] = []
        if spec.instructions_path is not None and spec.instructions_path != AGENTS_MD:
            links.append(root / spec.instructions_path)
        links.append(root / spec.skills_path)
        links.append(root / spec.subagents_path)

        for link in links:
            if link.is_symlink():
                parent = link.parent
                link.unlink()
                report.removed_symlinks.append(link)
                if parent != root:
                    parent_dirs.add(parent)

    for d in sorted(parent_dirs):
        if not any(d.iterdir()):
            d.rmdir()
            report.removed_dirs.append(d)
        else:
            report.nonempty_dirs.append(d)

    remaining = [n for n in current if n not in set(agent_names)]
    write_config(root, remaining)
    return report
