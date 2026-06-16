"""Entry points for the resident-expenses CLI."""

from __future__ import annotations

import sys
import webbrowser
from datetime import date
from pathlib import Path

import click

from resident_expenses.config import ConfigError, load_config
from resident_expenses.runner import run_report


@click.group()
def cli() -> None:
    """resident-expenses: reconcile a comunidad's accounts and build an HTML report."""


@cli.command()
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    default=Path("config.json"),
    envvar="RESIDENT_EXPENSES_CONFIG",
    show_envvar=True,
)
@click.option(
    "--output", "output_path", type=click.Path(path_type=Path), default=Path("report.html")
)
@click.option("--no-open", "no_open", is_flag=True, default=False)
def report(config_path: Path, output_path: Path, no_open: bool) -> None:
    """Build report.html from the data/ JSON files."""
    try:
        cfg = load_config(config_path)
    except ConfigError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    summary = run_report(cfg, output_path, today=date.today())
    click.echo(f"Parsed {summary['years']} year(s); {summary['alerts']} alert(s).")
    click.echo(f"Report written to {output_path}")
    if not no_open:
        webbrowser.open(output_path.resolve().as_uri())
