from __future__ import annotations

import shutil
from pathlib import Path
from typing import Annotated, Optional

import typer

from .agents import AGENT_REGISTRY
from .config import ConfigError, read_agent_names
from .harness import HarnessError, add as harness_add, init as harness_init, remove as harness_remove
from .status import check_all

app = typer.Typer(
    no_args_is_help=True,
    help="Manage projects targeting multiple coding agents from a shared harness.",
)


@app.callback()
def _callback() -> None:
    """multi-harness — shared harness for multi-agent coding projects."""


def _parse_agents(value: Optional[str]) -> list[str]:
    if value is None:
        return list(AGENT_REGISTRY)
    names = [n.strip() for n in value.split(",") if n.strip()]
    if not names:
        raise typer.BadParameter("--agents must list at least one agent.")
    return names


@app.command()
def init(
    path: Annotated[
        Path,
        typer.Argument(
            help="Project directory to initialize. Defaults to the current dir.",
            file_okay=False,
            dir_okay=True,
            exists=True,
            resolve_path=True,
        ),
    ] = Path("."),
    agents: Annotated[
        Optional[str],
        typer.Option(
            "--agents",
            help=(
                "Comma-separated list of agents to register. "
                f"Defaults to all supported: {','.join(AGENT_REGISTRY)}."
            ),
        ),
    ] = None,
    template: Annotated[
        Optional[Path],
        typer.Option(
            "--template",
            help="Path to a file used to seed AGENTS.md when it doesn't already exist.",
            file_okay=True,
            dir_okay=False,
            exists=True,
            readable=True,
            resolve_path=True,
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Re-link symlinks even if .harness/ already exists. Never overwrites real files.",
        ),
    ] = False,
) -> None:
    """Bootstrap or migrate a project into the multi-harness layout."""
    selected = _parse_agents(agents)
    try:
        report = harness_init(path, selected, template=template, force=force)
    except HarnessError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    if report.detected:
        names = ", ".join(s.display_name for s in report.detected)
        typer.echo(f"Detected existing agent: {names}")
    for src, dst in report.moved:
        typer.echo(f"  moved   {src.relative_to(path)} -> {dst.relative_to(path)}")
    for created in report.created_files:
        typer.echo(f"  created {created.relative_to(path)}")
    for link, result in report.symlinks:
        typer.echo(f"  link    {link.relative_to(path)} ({result})")
    typer.echo("Done.")


@app.command()
def add(
    agents: Annotated[
        list[str],
        typer.Argument(help="Agent name(s) to register."),
    ],
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            help="Project directory. Defaults to the current dir.",
            file_okay=False,
            dir_okay=True,
            exists=True,
            resolve_path=True,
        ),
    ] = Path("."),
) -> None:
    """Register one or more new agents to an existing harness."""
    try:
        report = harness_add(path, agents)
    except HarnessError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    for link, result in report.symlinks:
        typer.echo(f"  link    {link.relative_to(path)} ({result})")
    typer.echo("Done.")


@app.command()
def remove(
    agents: Annotated[
        list[str],
        typer.Argument(help="Agent name(s) to remove."),
    ],
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            help="Project directory. Defaults to the current dir.",
            file_okay=False,
            dir_okay=True,
            exists=True,
            resolve_path=True,
        ),
    ] = Path("."),
) -> None:
    """Remove one or more agents from the harness."""
    try:
        report = harness_remove(path, agents)
    except HarnessError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    for link in report.removed_symlinks:
        typer.echo(f"  unlinked {link.relative_to(path)}")
    for d in report.removed_dirs:
        typer.echo(f"  removed  {d.relative_to(path)}")
    for d in report.nonempty_dirs:
        rel = d.relative_to(path)
        if typer.confirm(f"  {rel} is not empty. Remove it?", default=False):
            shutil.rmtree(d)
            typer.echo(f"  removed  {rel}")
    typer.echo("Done.")


@app.command()
def status(
    path: Annotated[
        Path,
        typer.Argument(
            help="Project directory to check. Defaults to the current dir.",
            file_okay=False,
            dir_okay=True,
            exists=True,
            resolve_path=True,
        ),
    ] = Path("."),
) -> None:
    """Show symlink health for all registered agents."""
    try:
        agent_names = read_agent_names(path)
    except ConfigError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    statuses = check_all(path, agent_names)
    if not statuses:
        typer.echo("No agents registered.")
        return

    _STATUS_COLOR = {
        "ok": typer.colors.GREEN,
        "missing": typer.colors.YELLOW,
        "broken": typer.colors.RED,
        "detached": typer.colors.RED,
    }
    max_label = max(len(r.label) for s in statuses for r in s.rows)
    for agent_status in statuses:
        typer.echo(agent_status.spec.display_name)
        for row in agent_status.rows:
            typer.echo(f"  {row.label.ljust(max_label + 2)}", nl=False)
            typer.secho(row.status, fg=_STATUS_COLOR[row.status])
        typer.echo("")

    if not all(s.is_ok() for s in statuses):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
