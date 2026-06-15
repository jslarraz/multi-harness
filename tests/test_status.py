from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from multi_harness.agents import AGENT_REGISTRY
from multi_harness.cli import app
from multi_harness.config import (
    HARNESS_CONFIG,
    ConfigError,
    read_agent_names,
    write_config,
)
from multi_harness.harness import AGENTS_MD, HARNESS_AGENTS, HARNESS_SKILLS, init as harness_init
from multi_harness.status import AgentStatus, check_agent, check_all, check_symlink

ALL_AGENTS = list(AGENT_REGISTRY)


# ---------------------------------------------------------------------------
# check_symlink unit tests
# ---------------------------------------------------------------------------


def test_check_symlink_ok(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(Path(os.path.relpath(target, start=link.parent)))
    assert check_symlink(link, target) == "ok"


def test_check_symlink_missing(tmp_path: Path) -> None:
    link = tmp_path / "link"
    target = tmp_path / "target"
    assert check_symlink(link, target) == "missing"


def test_check_symlink_detached(tmp_path: Path) -> None:
    link = tmp_path / "link"
    link.mkdir()
    target = tmp_path / "target"
    assert check_symlink(link, target) == "detached"


def test_check_symlink_broken_dangling(tmp_path: Path) -> None:
    target = tmp_path / "ghost"
    link = tmp_path / "link"
    link.symlink_to(Path(os.path.relpath(target, start=link.parent)))
    assert check_symlink(link, target) == "ok"  # target doesn't exist yet, but that's "ok" direction
    # Actually we need a dangling symlink pointing somewhere the target is NOT expected_target
    # Let's make a symlink to a nonexistent path that differs from expected_target
    link.unlink()
    other = tmp_path / "other_nonexistent"
    link.symlink_to(Path(os.path.relpath(other, start=link.parent)))
    assert check_symlink(link, target) == "broken"


def test_check_symlink_broken_wrong_target(tmp_path: Path) -> None:
    wrong = tmp_path / "wrong"
    wrong.mkdir()
    expected = tmp_path / "expected"
    expected.mkdir()
    link = tmp_path / "link"
    link.symlink_to(Path(os.path.relpath(wrong, start=link.parent)))
    assert check_symlink(link, expected) == "broken"


# ---------------------------------------------------------------------------
# write_config / read_agent_names unit tests
# ---------------------------------------------------------------------------


def test_write_config_round_trip(tmp_path: Path) -> None:
    (tmp_path / ".harness").mkdir()
    write_config(tmp_path, ["claude", "codex"])
    assert read_agent_names(tmp_path) == ["claude", "codex"]


def test_read_agent_names_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        read_agent_names(tmp_path)


def test_read_agent_names_malformed_toml(tmp_path: Path) -> None:
    (tmp_path / ".harness").mkdir()
    (tmp_path / HARNESS_CONFIG).write_text("not valid toml = [[[")
    with pytest.raises(ConfigError, match="malformed"):
        read_agent_names(tmp_path)


def test_read_agent_names_missing_agents_key(tmp_path: Path) -> None:
    (tmp_path / ".harness").mkdir()
    (tmp_path / HARNESS_CONFIG).write_text("[harness]\nversion = 1\n")
    with pytest.raises(ConfigError, match="missing key"):
        read_agent_names(tmp_path)


# ---------------------------------------------------------------------------
# check_agent integration tests
# ---------------------------------------------------------------------------


def test_check_agent_all_ok_after_init(project: Path) -> None:
    harness_init(project, ["claude"])
    agent_status = check_agent(project, AGENT_REGISTRY["claude"])
    assert agent_status.is_ok()
    assert all(r.status == "ok" for r in agent_status.rows)


def test_check_agent_missing_after_unlink(project: Path) -> None:
    harness_init(project, ["claude"])
    (project / ".claude/skills").unlink()
    agent_status = check_agent(project, AGENT_REGISTRY["claude"])
    skills_row = next(r for r in agent_status.rows if r.label == ".claude/skills")
    assert skills_row.status == "missing"
    assert not agent_status.is_ok()


def test_check_agent_detached(project: Path) -> None:
    harness_init(project, ["claude"])
    (project / ".claude/agents").unlink()
    (project / ".claude/agents").mkdir()
    agent_status = check_agent(project, AGENT_REGISTRY["claude"])
    agents_row = next(r for r in agent_status.rows if r.label == ".claude/agents")
    assert agents_row.status == "detached"


def test_check_agent_broken_wrong_target(project: Path, tmp_path: Path) -> None:
    harness_init(project, ["claude"])
    link = project / ".claude/skills"
    link.unlink()
    other = tmp_path / "other"
    other.mkdir()
    link.symlink_to(Path(os.path.relpath(other, start=link.parent)))
    agent_status = check_agent(project, AGENT_REGISTRY["claude"])
    skills_row = next(r for r in agent_status.rows if r.label == ".claude/skills")
    assert skills_row.status == "broken"


def test_check_agent_native_has_no_instructions_row(project: Path) -> None:
    harness_init(project, ["codex"])
    agent_status = check_agent(project, AGENT_REGISTRY["codex"])
    labels = [r.label for r in agent_status.rows]
    assert len(labels) == 2
    assert ".codex/skills" in labels
    assert ".codex/agents" in labels


def test_check_all_returns_registered_agents_only(project: Path) -> None:
    harness_init(project, ["claude", "codex"])
    statuses = check_all(project, ["claude", "codex"])
    assert len(statuses) == 2
    names = {s.spec.name for s in statuses}
    assert names == {"claude", "codex"}


# ---------------------------------------------------------------------------
# mh init writes config.toml
# ---------------------------------------------------------------------------


def test_init_writes_config_toml(project: Path) -> None:
    harness_init(project, ["claude", "codex"])
    assert (project / HARNESS_CONFIG).exists()
    assert read_agent_names(project) == ["claude", "codex"]


def test_init_force_overwrites_config(project: Path) -> None:
    harness_init(project, ["claude"])
    assert read_agent_names(project) == ["claude"]
    harness_init(project, ["claude", "codex"], force=True)
    assert read_agent_names(project) == ["claude", "codex"]


# ---------------------------------------------------------------------------
# mh status CLI tests
# ---------------------------------------------------------------------------


def test_cli_status_ok_after_init(project: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init", str(project)])
    result = runner.invoke(app, ["status", str(project)])
    assert result.exit_code == 0, result.output
    for spec in AGENT_REGISTRY.values():
        assert spec.display_name in result.output


def test_cli_status_exits_nonzero_on_missing_link(project: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init", str(project)])
    (project / ".claude/skills").unlink()
    result = runner.invoke(app, ["status", str(project)])
    assert result.exit_code != 0


def test_cli_status_no_config_exits_nonzero(project: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["status", str(project)])
    assert result.exit_code != 0
    assert "error" in result.output or "error" in (result.stderr or "")


def test_cli_status_output_contains_ok(project: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init", str(project)])
    result = runner.invoke(app, ["status", str(project)])
    assert "ok" in result.output


def test_cli_status_subset_agents(project: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init", str(project), "--agents", "claude"])
    result = runner.invoke(app, ["status", str(project)])
    assert result.exit_code == 0
    assert "Claude Code" in result.output
    assert "OpenAI Codex" not in result.output


def test_cli_status_no_registered_agents(project: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init", str(project), "--agents", "claude"])
    runner.invoke(app, ["remove", "claude", "--path", str(project)])

    result = runner.invoke(app, ["status", str(project)])

    assert result.exit_code == 0
    assert "No agents registered." in result.output


def test_cli_status_detached_shows_in_output(project: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init", str(project), "--agents", "claude"])
    (project / ".claude/agents").unlink()
    (project / ".claude/agents").mkdir()
    result = runner.invoke(app, ["status", str(project)])
    assert result.exit_code != 0
    assert "detached" in result.output


def test_cli_status_per_agent_table_format(project: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init", str(project), "--agents", "claude"])
    result = runner.invoke(app, ["status", str(project)])
    lines = result.output.splitlines()
    # First non-empty line should be the agent display name (no leading whitespace)
    display_lines = [l for l in lines if l.strip()]
    assert display_lines[0] == "Claude Code"
    # Subsequent rows should be indented
    indented = [l for l in display_lines[1:] if l]
    assert all(l.startswith("  ") for l in indented if l.strip())
