"""Assemble the slim ReportModel consumed by the renderer."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from datetime import date, timedelta

from resident_expenses.models import Alert, FiscalPeriod, ParsedYear, ReportModel


def _period(parsed: ParsedYear) -> FiscalPeriod | None:
    """The exercise's display window: first transaction date to the explicit
    exercise end (or last transaction date). Returns None for an empty exercise."""
    dates = [t.date for t in parsed.transactions]
    if not dates:
        return None
    return FiscalPeriod(
        year=parsed.year,
        start=min(dates),
        end=parsed.period_end or max(dates),
    )


def build_report_model(
    *,
    parsed_years: Iterable[ParsedYear],
    building_name: str,
    currency: str,
    generated_at: date,
    alerts: Iterable[Alert] = (),
) -> ReportModel:
    years = list(parsed_years)
    periods = [p for p in (_period(y) for y in years) if p is not None]
    # Fiscal exercises are contiguous: each begins the day after the prior one
    # closed. Walk them chronologically and pin each non-earliest period's start to
    # the previous period's end + 1 day, rather than its (later) first txn date.
    periods.sort(key=lambda p: p.year)
    prev_end: date | None = None
    for i, p in enumerate(periods):
        if prev_end is not None:
            periods[i] = replace(p, start=prev_end + timedelta(days=1))
        prev_end = p.end
    periods.sort(key=lambda p: p.year, reverse=True)
    return ReportModel(
        generated_at=generated_at,
        building_name=building_name,
        currency=currency,
        years=tuple(sorted({p.year for p in years}, reverse=True)),
        periods=tuple(periods),
        transactions=tuple(t for p in years for t in p.transactions),
        alerts=tuple(alerts),
    )
