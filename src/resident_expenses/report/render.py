"""Render a ReportModel as a single self-contained HTML file (home-expenses style).

All rendering happens client-side from an embedded JSON blob + inlined plotly.js:
year-tab filtering, KPI + per-category cards, a monthly income-vs-expenses chart, and
a category-colored transactions table with a clickable legend. Each transaction carries
a ``category`` (assigned upstream by the data source) that ties the chart, cards, and
table together via one color sequence.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import plotly  # type: ignore[import-untyped]
from jinja2 import Environment, FileSystemLoader, select_autoescape

from resident_expenses.models import FiscalPeriod, ReportModel

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _load_locales() -> dict[str, object]:
    data: dict[str, object] = json.loads(
        (_TEMPLATE_DIR / "locales.json").read_text(encoding="utf-8")
    )
    return data


def _period_heading(p: FiscalPeriod) -> str:
    """Fiscal-year heading, e.g. ``2023 / 2024`` (or a bare ``2023`` when the
    exercise stays within one calendar year)."""
    if p.start.year == p.end.year:
        return str(p.start.year)
    return f"{p.start.year} / {p.end.year}"


def _period_range(p: FiscalPeriod) -> str:
    """Day/month span, e.g. ``05/10 – 28/02``; the years live in the heading."""
    return f"{p.start.strftime('%d/%m')} – {p.end.strftime('%d/%m')}"


def _ordered_categories(model: ReportModel) -> list[str]:
    """Stable color/legend order, derived from the data (no hard-coded names):
    income categories first, then expense, each by descending total magnitude."""
    totals: dict[str, Decimal] = {}
    kind_rank: dict[str, int] = {}
    for t in model.transactions:
        totals[t.category] = totals.get(t.category, Decimal("0")) + abs(t.amount)
        kind_rank[t.category] = 0 if t.kind == "income" else 1
    return sorted(totals, key=lambda c: (kind_rank[c], -totals[c], c))


def _running_balances(model: ReportModel) -> tuple[list[Decimal], list[int]]:
    """Per-transaction running balance and chronological rank, both in
    ``model.transactions`` order.

    The balance is the account total after each transaction, accumulated from zero
    across the *whole* history; it is fixed per row, not recomputed when the client
    hides or filters rows. ``seq`` is the position in that same chronological order
    (date ascending, same-day ties broken by data-source position — a stable sort
    preserves the original ledger sequence). The table sorts by ``seq`` *descending*
    so the displayed order is the exact reverse of the accumulation: the newest
    transaction sits on top showing the final total, and each row's balance equals
    the row below it plus that row's own amount."""
    order = sorted(range(len(model.transactions)), key=lambda i: model.transactions[i].date)
    balances: list[Decimal] = [Decimal("0")] * len(model.transactions)
    seq: list[int] = [0] * len(model.transactions)
    running = Decimal("0")
    for rank, i in enumerate(order):
        running += model.transactions[i].amount
        balances[i] = running
        seq[i] = rank
    return balances, seq


def render_report(model: ReportModel, output_path: Path) -> None:
    balances, seq = _running_balances(model)
    txns = [
        {
            "date": t.date.isoformat(),
            "label": t.label,
            "amount": str(t.amount),
            "kind": t.kind,
            "category": t.category,
            # Fiscal exercise the row belongs to — the tab filter keys off this, not
            # the calendar year, so an exercise that spans two years stays one tab.
            "year": t.year,
            # Recorded but never occurred — drives a row marker; still counts in totals.
            "missing": t.missing,
            # Account balance after this transaction, fixed over the full history; the
            # client renders it verbatim and never recomputes it under filters.
            "balance": str(balances[idx]),
            # Chronological rank (date asc, same-day ties by data-source position).
            # The table sorts by this descending so the balance column reads as a
            # consistent running total, independent of same-date string sorting.
            "seq": seq[idx],
        }
        for idx, t in enumerate(model.transactions)
    ]
    ordered = _ordered_categories(model)

    # One selector tab per fiscal exercise (newest first), shown as a three-line
    # label: an exercise ordinal over a fiscal-year heading over a day/month range.
    # A fiscal exercise spans two calendar years, e.g. Oct 2023 – Feb 2024.
    # model.periods is newest-first; the oldest exercise is "YEAR 1" and the count
    # rises forward in time, so the newest (index 0) carries the highest number.
    total = len(model.periods)
    periods = [
        {
            "year": p.year,
            "index": total - i,
            "heading": _period_heading(p),
            "range": _period_range(p),
            # ISO bounds let the client compute the Period KPI (range + day count),
            # which follows the year tab only and ignores the income/expense filter.
            "start": p.start.isoformat(),
            "end": p.end.isoformat(),
        }
        for i, p in enumerate(model.periods)
    ]

    data = {
        "currency": model.currency,
        "building_name": model.building_name,
        "generated_at": model.generated_at.isoformat(),
        "periods": periods,
        "categories": ordered,
        "transactions": txns,
        # Alerts are rendered (and localized) client-side from kind + payload, so the
        # server-side English message is intentionally not embedded into the blob.
        "alerts": [{"kind": a.kind.value, "payload": a.payload} for a in model.alerts],
    }

    env = Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "j2"]),
    )
    template = env.get_template("report.html.j2")
    html = template.render(
        model=model,
        periods=periods,
        plotly_js=plotly.offline.get_plotlyjs(),
        data_json=json.dumps(data, ensure_ascii=False),
        locales_json=json.dumps(_load_locales(), ensure_ascii=False),
    )
    output_path.write_text(html, encoding="utf-8")
