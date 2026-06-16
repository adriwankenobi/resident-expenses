"""Orchestrate parse → reconcile → model → render."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path

from resident_expenses.config import Config
from resident_expenses.data_json import load_year
from resident_expenses.models import Alert, ParsedYear
from resident_expenses.reconcile import run_checks
from resident_expenses.report.model import build_report_model
from resident_expenses.report.render import render_report


def run_report_from_data(
    *,
    parsed_years: Sequence[ParsedYear],
    building_name: str,
    currency: str,
    output_path: Path,
    today: date,
) -> dict[str, int]:
    alerts: list[Alert] = []
    for parsed in parsed_years:
        alerts.extend(run_checks(parsed))

    model = build_report_model(
        parsed_years=parsed_years,
        building_name=building_name,
        currency=currency,
        generated_at=today,
        alerts=alerts,
    )
    render_report(model, output_path)
    return {"years": len(parsed_years), "alerts": len(alerts)}


def run_report(cfg: Config, output_path: Path, today: date) -> dict[str, int]:
    year_files = sorted(cfg.data_dir.glob("[0-9][0-9][0-9][0-9].json"))
    parsed_years = [load_year(p) for p in year_files]
    return run_report_from_data(
        parsed_years=parsed_years,
        building_name=cfg.building_name,
        currency=cfg.currency,
        output_path=output_path,
        today=today,
    )
