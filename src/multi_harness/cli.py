from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from .agents import AGENT_REGISTRY
from .harness import HarnessError, init as harness_init

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


if __name__ == "__main__":
    app()
