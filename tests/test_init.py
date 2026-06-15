from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from multi_harness.agents import AGENT_REGISTRY
from multi_harness.cli import app
from multi_harness.harness import (
    AGENTS_MD,
    HARNESS_AGENTS,
    HARNESS_DIR,
    HARNESS_SKILLS,
    HarnessError,
    detect_configured_agents,
    init as harness_init,
)

ALL_AGENTS = list(AGENT_REGISTRY)


def assert_symlink_to(link: Path, expected_target: Path) -> None:
    assert link.is_symlink(), f"{link} is not a symlink"
    actual_rel = os.readlink(link)
    assert not os.path.isabs(actual_rel), f"{link} symlink is absolute: {actual_rel}"
    resolved = (link.parent / actual_rel).resolve()
    assert resolved == expected_target.resolve(), (
        f"{link} -> {actual_rel} resolves to {resolved}, expected {expected_target.resolve()}"
    )


def test_fresh_init_all_agents(project: Path) -> None:
    harness_init(project, ALL_AGENTS)

    assert (project / AGENTS_MD).is_file()
    assert (project / AGENTS_MD).read_text() == ""
    assert (project / HARNESS_SKILLS).is_dir()
    assert (project / HARNESS_AGENTS).is_dir()

    for spec in AGENT_REGISTRY.values():
        if spec.instructions_path and spec.instructions_path != AGENTS_MD:
            assert_symlink_to(project / spec.instructions_path, project / AGENTS_MD)
        assert_symlink_to(project / spec.skills_path, project / HARNESS_SKILLS)
        assert_symlink_to(project / spec.subagents_path, project / HARNESS_AGENTS)


def test_fresh_init_subset(project: Path) -> None:
    harness_init(project, ["claude", "codex"])

    assert (project / ".claude/skills").is_symlink()
    assert (project / ".codex/skills").is_symlink()
    # Other agent directories must not be created.
    assert not (project / ".opencode").exists()
    assert not (project / ".github").exists()
    assert not (project / ".agents").exists()
    assert not (project / ".subagents").exists()


def test_migration_from_claude(project: Path, helpers) -> None:
    helpers.make_file(project / "CLAUDE.md", "# my claude rules\n")
    helpers.make_file(project / ".claude/skills/foo/SKILL.md", "skill body")
    helpers.make_file(project / ".claude/agents/bar.md", "agent body")
    helpers.make_file(project / ".claude/settings.json", "{}")  # must be left alone

    harness_init(project, ALL_AGENTS)

    # AGENTS.md now contains the original CLAUDE.md content
    assert (project / AGENTS_MD).read_text() == "# my claude rules\n"
    # CLAUDE.md is now a symlink back to AGENTS.md
    assert_symlink_to(project / "CLAUDE.md", project / AGENTS_MD)
    # .claude/skills and .claude/agents are symlinks into .harness
    assert_symlink_to(project / ".claude/skills", project / HARNESS_SKILLS)
    assert_symlink_to(project / ".claude/agents", project / HARNESS_AGENTS)
    # Real files relocated under .harness/
    assert (project / HARNESS_SKILLS / "foo/SKILL.md").read_text() == "skill body"
    assert (project / HARNESS_AGENTS / "bar.md").read_text() == "agent body"
    # Untouched agent-specific file
    assert (project / ".claude/settings.json").is_file()


def test_migration_from_codex(project: Path, helpers) -> None:
    helpers.make_file(project / AGENTS_MD, "# already exists\n")
    helpers.make_file(project / ".codex/skills/a/SKILL.md", "x")
    helpers.make_file(project / ".codex/agents/b.md", "y")

    harness_init(project, ALL_AGENTS)

    assert (project / AGENTS_MD).read_text() == "# already exists\n"
    assert (project / HARNESS_SKILLS / "a/SKILL.md").read_text() == "x"
    assert (project / HARNESS_AGENTS / "b.md").read_text() == "y"
    assert_symlink_to(project / ".codex/skills", project / HARNESS_SKILLS)
    assert_symlink_to(project / ".codex/agents", project / HARNESS_AGENTS)


def test_migration_from_opencode_singular_agent(project: Path, helpers) -> None:
    helpers.make_file(project / ".opencode/skills/s/SKILL.md", "s")
    helpers.make_file(project / ".opencode/agent/a.md", "a")  # NB singular

    harness_init(project, ALL_AGENTS)

    assert (project / HARNESS_AGENTS / "a.md").read_text() == "a"
    assert_symlink_to(project / ".opencode/skills", project / HARNESS_SKILLS)
    assert_symlink_to(project / ".opencode/agent", project / HARNESS_AGENTS)


def test_multi_agent_detected_errors(project: Path, helpers) -> None:
    helpers.make_file(project / "CLAUDE.md", "claude")
    helpers.make_dir(project / ".codex")

    with pytest.raises(HarnessError, match="More than one agent"):
        harness_init(project, ALL_AGENTS)

    # Nothing should have been modified on the filesystem.
    assert not (project / HARNESS_DIR).exists()
    assert (project / "CLAUDE.md").read_text() == "claude"


def test_detection_ignores_symlink_markers(project: Path) -> None:
    (project / AGENTS_MD).touch()
    (project / "CLAUDE.md").symlink_to("AGENTS.md")
    (project / ".subagents").symlink_to(".harness/agents")

    detected = detect_configured_agents(project)

    assert detected == []


def test_harness_exists_without_force_errors(project: Path) -> None:
    (project / HARNESS_DIR).mkdir()
    with pytest.raises(HarnessError, match="already exists"):
        harness_init(project, ALL_AGENTS)


def test_harness_exists_with_force_is_idempotent(project: Path) -> None:
    harness_init(project, ALL_AGENTS)
    # Drop a real file inside .harness/skills to confirm we don't touch contents.
    (project / HARNESS_SKILLS / "keep.md").write_text("keep me")

    harness_init(project, ALL_AGENTS, force=True)

    assert (project / HARNESS_SKILLS / "keep.md").read_text() == "keep me"
    # Symlinks still correct.
    assert_symlink_to(project / ".claude/skills", project / HARNESS_SKILLS)


def test_symlink_collision_with_real_dir_aborts(project: Path, helpers) -> None:
    # Pre-existing real .claude/skills dir, but no CLAUDE.md and no .claude marker
    # that triggers migration (we create it ourselves so detection still fires).
    helpers.make_file(project / ".claude/skills/preexisting.md", "pre")
    # Also pre-create .harness/skills so the migration step fails on rename.
    (project / HARNESS_SKILLS).mkdir(parents=True)
    (project / HARNESS_SKILLS / "existing.md").write_text("existing")

    with pytest.raises(HarnessError):
        harness_init(project, ALL_AGENTS, force=True)

    # User data preserved.
    assert (project / ".claude/skills/preexisting.md").read_text() == "pre"
    assert (project / HARNESS_SKILLS / "existing.md").read_text() == "existing"


def test_symlinks_are_relative_and_portable(project: Path, tmp_path_factory) -> None:
    harness_init(project, ALL_AGENTS)

    moved = tmp_path_factory.mktemp("moved") / "proj"
    shutil.move(str(project), str(moved))

    # Symlinks resolve to the moved tree, not the original location.
    for spec in AGENT_REGISTRY.values():
        link = moved / spec.skills_path
        assert link.is_symlink()
        assert link.resolve() == (moved / HARNESS_SKILLS).resolve()


def test_template_seeds_agents_md_and_is_not_overwritten(
    project: Path, helpers, tmp_path_factory
) -> None:
    tpl1 = tmp_path_factory.mktemp("tpl") / "first.md"
    tpl1.write_text("FIRST TEMPLATE\n")
    tpl2 = tmp_path_factory.mktemp("tpl2") / "second.md"
    tpl2.write_text("SECOND TEMPLATE\n")

    harness_init(project, ALL_AGENTS, template=tpl1)
    assert (project / AGENTS_MD).read_text() == "FIRST TEMPLATE\n"

    harness_init(project, ALL_AGENTS, template=tpl2, force=True)
    assert (project / AGENTS_MD).read_text() == "FIRST TEMPLATE\n"


def test_cli_unknown_agent_errors(project: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["init", str(project), "--agents", "nosuchagent"])
    assert result.exit_code != 0
    assert "Unknown agent" in result.stderr or "Unknown agent" in result.output


def test_cli_fresh_init_default_path(project: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["init", str(project)])
    assert result.exit_code == 0, result.output
    assert (project / AGENTS_MD).exists()
    assert (project / HARNESS_DIR).is_dir()
