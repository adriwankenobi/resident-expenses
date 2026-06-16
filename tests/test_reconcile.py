from dataclasses import replace
from datetime import date
from decimal import Decimal

from resident_expenses.models import (
    AlertKind,
    ParsedYear,
    Transaction,
)
from resident_expenses.reconcile import (
    check_missing_transactions,
    check_summary_mismatch,
)


def _income(
    month: int, amount: str, label: str = "Cuotas mes", category: str = "Cuotas ordinarias"
) -> Transaction:
    return Transaction(
        date=date(2025, month, 10),
        label=label,
        amount=Decimal(amount),
        year=2025,
        category=category,
    )


def _expense(month: int, amount: str, label: str, category: str = "Otros gastos") -> Transaction:
    return Transaction(
        date=date(2025, month, 15),
        label=label,
        amount=Decimal(amount),
        year=2025,
        category=category,
    )


def _parsed(txns: tuple[Transaction, ...], end: date) -> ParsedYear:
    return ParsedYear(
        year=2025,
        transactions=txns,
        summary_income=Decimal("0"),
        summary_expense=Decimal("0"),
        period_end=end,
    )


def test_summary_mismatch_detects_drift() -> None:
    py = ParsedYear(
        year=2025,
        transactions=(_income(1, "100.00"), _expense(1, "-40.00", "Limpieza")),
        summary_income=Decimal("999.00"),  # wrong on purpose
        summary_expense=Decimal("-40.00"),
    )
    alerts = check_summary_mismatch(py)
    assert len(alerts) == 1
    assert alerts[0].kind == AlertKind.SUMMARY_MISMATCH
    assert alerts[0].payload["field"] == "income"


def test_summary_mismatch_silent_when_consistent() -> None:
    py = ParsedYear(
        year=2025,
        transactions=(_income(1, "100.00"), _expense(1, "-40.00", "Limpieza")),
        summary_income=Decimal("100.00"),
        summary_expense=Decimal("-40.00"),
    )
    assert check_summary_mismatch(py) == []


def test_missing_transactions_emits_one_alert_each() -> None:
    txns = (
        replace(_income(1, "100.00"), missing=True),
        _income(2, "100.00"),
        replace(_expense(3, "-50.00", "Reparación"), missing=True),
    )
    parsed = _parsed(txns, date(2025, 12, 31))
    alerts = check_missing_transactions(parsed)
    assert len(alerts) == 2
    assert all(a.kind == AlertKind.MISSING_TRANSACTION for a in alerts)
    payload = alerts[0].payload
    assert payload["year"] == 2025
    assert payload["date"] == "2025-01-10"
    assert payload["amount"] == "100.00"
    assert payload["kind"] == "income"
    assert "label" in payload


def test_no_missing_transactions_no_alerts() -> None:
    parsed = _parsed((_income(1, "100.00"),), date(2025, 12, 31))
    assert check_missing_transactions(parsed) == []
