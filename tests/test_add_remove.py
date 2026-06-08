from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from multi_harness.agents import AGENT_REGISTRY
from multi_harness.cli import app
from multi_harness.config import read_agent_names
from multi_harness.harness import (
    HARNESS_AGENTS,
    HARNESS_DIR,
    HARNESS_SKILLS,
    HarnessError,
    add as harness_add,
    init as harness_init,
    remove as harness_remove,
)
from tests.test_init import assert_symlink_to


# ---------------------------------------------------------------------------
# mh add
# ---------------------------------------------------------------------------

def test_add_new_agent(project: Path) -> None:
    harness_init(project, ["claude", "codex"])
    harness_add(project, ["opencode"])

    assert_symlink_to(project / ".opencode/skills", project / HARNESS_SKILLS)
    assert_symlink_to(project / ".opencode/agent", project / HARNESS_AGENTS)
    assert read_agent_names(project) == ["claude", "codex", "opencode"]


def test_add_multiple_agents_at_once(project: Path) -> None:
    harness_init(project, ["claude"])
    harness_add(project, ["codex", "opencode"])

    assert_symlink_to(project / ".codex/skills", project / HARNESS_SKILLS)
    assert_symlink_to(project / ".opencode/skills", project / HARNESS_SKILLS)
    assert set(read_agent_names(project)) == {"claude", "codex", "opencode"}


def test_add_unknown_agent_errors(project: Path) -> None:
    harness_init(project, ["claude"])
    with pytest.raises(HarnessError, match="Unknown agent"):
        harness_add(project, ["nosuchagent"])


def test_add_already_registered_errors(project: Path) -> None:
    harness_init(project, ["claude"])
    with pytest.raises(HarnessError, match="already registered"):
        harness_add(project, ["claude"])


def test_add_no_harness_errors(project: Path) -> None:
    with pytest.raises(HarnessError, match="not found"):
        harness_add(project, ["claude"])


def test_add_does_not_touch_existing_symlinks(project: Path) -> None:
    harness_init(project, ["claude", "codex"])
    (project / HARNESS_SKILLS / "keep.md").write_text("keep")
    harness_add(project, ["opencode"])
    assert (project / HARNESS_SKILLS / "keep.md").read_text() == "keep"
    assert_symlink_to(project / ".claude/skills", project / HARNESS_SKILLS)


def test_cli_add(project: Path) -> None:
    harness_init(project, ["claude"])
    runner = CliRunner()
    result = runner.invoke(app, ["add", "codex", "--path", str(project)])
    assert result.exit_code == 0, result.output
    assert (project / ".codex/skills").is_symlink()
    assert "Done." in result.output


def test_cli_add_unknown_agent_errors(project: Path) -> None:
    harness_init(project, ["claude"])
    runner = CliRunner()
    result = runner.invoke(app, ["add", "nosuchagent", "--path", str(project)])
    assert result.exit_code != 0


def test_cli_add_already_registered_errors(project: Path) -> None:
    harness_init(project, ["claude"])
    runner = CliRunner()
    result = runner.invoke(app, ["add", "claude", "--path", str(project)])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# mh remove
# ---------------------------------------------------------------------------

def test_remove_unlinks_symlinks(project: Path) -> None:
    harness_init(project, ["claude", "codex"])
    harness_remove(project, ["codex"])

    assert not (project / ".codex/skills").exists()
    assert not (project / ".codex/agents").exists()
    assert read_agent_names(project) == ["claude"]


def test_remove_cleans_up_empty_parent_dir(project: Path) -> None:
    harness_init(project, ["codex"])
    report = harness_remove(project, ["codex"])

    assert not (project / ".codex").exists()
    assert project / ".codex" in report.removed_dirs


def test_remove_leaves_nonempty_parent_dir(project: Path, helpers) -> None:
    harness_init(project, ["claude"])
    helpers.make_file(project / ".claude/settings.json", "{}")

    report = harness_remove(project, ["claude"])

    assert (project / ".claude").is_dir()
    assert (project / ".claude/settings.json").exists()
    assert project / ".claude" in report.nonempty_dirs
    assert project / ".claude" not in report.removed_dirs


def test_remove_all_agents_allowed(project: Path) -> None:
    harness_init(project, ["claude", "codex"])
    harness_remove(project, ["claude", "codex"])

    assert read_agent_names(project) == []
    assert (project / HARNESS_DIR).exists()


def test_remove_updates_config(project: Path) -> None:
    harness_init(project, ["claude", "codex", "opencode"])
    harness_remove(project, ["codex"])
    assert read_agent_names(project) == ["claude", "opencode"]


def test_remove_unknown_agent_errors(project: Path) -> None:
    harness_init(project, ["claude"])
    with pytest.raises(HarnessError, match="Unknown agent"):
        harness_remove(project, ["nosuchagent"])


def test_remove_not_registered_errors(project: Path) -> None:
    harness_init(project, ["claude"])
    with pytest.raises(HarnessError, match="not registered"):
        harness_remove(project, ["codex"])


def test_remove_no_harness_errors(project: Path) -> None:
    with pytest.raises(HarnessError, match="not found"):
        harness_remove(project, ["claude"])


def test_remove_skips_absent_symlinks(project: Path) -> None:
    harness_init(project, ["codex"])
    (project / ".codex/skills").unlink()

    report = harness_remove(project, ["codex"])
    assert project / ".codex/skills" not in report.removed_symlinks


def test_cli_remove(project: Path) -> None:
    harness_init(project, ["claude", "codex"])
    runner = CliRunner()
    result = runner.invoke(app, ["remove", "codex", "--path", str(project)])
    assert result.exit_code == 0, result.output
    assert not (project / ".codex/skills").exists()
    assert "Done." in result.output


def test_cli_remove_confirms_nonempty_dir_yes(project: Path, helpers) -> None:
    harness_init(project, ["claude"])
    helpers.make_file(project / ".claude/settings.json", "{}")

    runner = CliRunner()
    result = runner.invoke(
        app, ["remove", "claude", "--path", str(project)], input="y\n"
    )
    assert result.exit_code == 0, result.output
    assert not (project / ".claude").exists()


def test_cli_remove_confirms_nonempty_dir_no(project: Path, helpers) -> None:
    harness_init(project, ["claude"])
    helpers.make_file(project / ".claude/settings.json", "{}")

    runner = CliRunner()
    result = runner.invoke(
        app, ["remove", "claude", "--path", str(project)], input="n\n"
    )
    assert result.exit_code == 0, result.output
    assert (project / ".claude").is_dir()
    assert (project / ".claude/settings.json").exists()


def test_cli_remove_unknown_agent_errors(project: Path) -> None:
    harness_init(project, ["claude"])
    runner = CliRunner()
    result = runner.invoke(app, ["remove", "nosuchagent", "--path", str(project)])
    assert result.exit_code != 0


def test_cli_remove_not_registered_errors(project: Path) -> None:
    harness_init(project, ["claude"])
    runner = CliRunner()
    result = runner.invoke(app, ["remove", "codex", "--path", str(project)])
    assert result.exit_code != 0
