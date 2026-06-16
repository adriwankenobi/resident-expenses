"""Reconciliation checks producing Alerts.

Each check is pure: it takes parsed data and returns a list of Alerts.
"""

from __future__ import annotations

from decimal import Decimal

from resident_expenses.models import (
    Alert,
    AlertKind,
    ParsedYear,
)


def check_missing_transactions(parsed: ParsedYear) -> list[Alert]:
    """One alert per transaction flagged ``missing`` (recorded but never occurred).

    Informational only: the amount still counts toward totals, so this does not affect
    the summary check. The label/amount live solely in the (encrypted) report.
    """
    alerts: list[Alert] = []
    for t in parsed.transactions:
        if not t.missing:
            continue
        alerts.append(
            Alert(
                kind=AlertKind.MISSING_TRANSACTION,
                message=(
                    f"{parsed.year}: recorded but did not occur: {t.label!r} ({t.date.isoformat()})"
                ),
                payload={
                    "year": parsed.year,
                    "date": t.date.isoformat(),
                    "label": t.label,
                    "amount": str(t.amount),
                    "kind": t.kind,
                },
            )
        )
    return alerts


def check_summary_mismatch(parsed: ParsedYear) -> list[Alert]:
    computed_income = sum(
        (t.amount for t in parsed.transactions if t.kind == "income"), Decimal("0")
    )
    computed_expense = sum(
        (t.amount for t in parsed.transactions if t.kind == "expense"), Decimal("0")
    )
    alerts: list[Alert] = []
    if computed_income != parsed.summary_income:
        alerts.append(
            Alert(
                kind=AlertKind.SUMMARY_MISMATCH,
                message=(
                    f"{parsed.year}: computed income {computed_income} != "
                    f"stated summary {parsed.summary_income}"
                ),
                payload={
                    "year": parsed.year,
                    "field": "income",
                    "computed": str(computed_income),
                    "summary": str(parsed.summary_income),
                },
            )
        )
    if computed_expense != parsed.summary_expense:
        alerts.append(
            Alert(
                kind=AlertKind.SUMMARY_MISMATCH,
                message=(
                    f"{parsed.year}: computed expense {computed_expense} != "
                    f"stated summary {parsed.summary_expense}"
                ),
                payload={
                    "year": parsed.year,
                    "field": "expense",
                    "computed": str(computed_expense),
                    "summary": str(parsed.summary_expense),
                },
            )
        )
    return alerts


def run_checks(parsed: ParsedYear) -> list[Alert]:
    return [
        *check_summary_mismatch(parsed),
        *check_missing_transactions(parsed),
    ]
