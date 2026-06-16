from datetime import date
from decimal import Decimal

from resident_expenses.models import (
    Alert,
    AlertKind,
    ParsedYear,
    Transaction,
)


def test_kind_is_derived_from_amount_sign() -> None:
    expense = Transaction(
        date=date(2025, 3, 10), label="Calefacción", amount=Decimal("-120.50"), year=2025
    )
    assert expense.kind == "expense"
    income = Transaction(date=date(2025, 3, 10), label="Cuota", amount=Decimal("120.50"), year=2025)
    assert income.kind == "income"


def test_zero_amount_is_income() -> None:
    t = Transaction(date=date(2025, 3, 10), label="Ajuste", amount=Decimal("0"), year=2025)
    assert t.kind == "income"


def test_explicit_kind_overrides_sign() -> None:
    # A reversal inside the income section: negative amount, but it is income.
    reversal = Transaction(
        date=date(2023, 12, 21),
        label="Transferencia a AELCA",
        amount=Decimal("-383.00"),
        year=2024,
        kind="income",
    )
    assert reversal.kind == "income"
    # And the converse: a positive amount explicitly marked as an expense.
    refund = Transaction(
        date=date(2024, 1, 1), label="Devolución", amount=Decimal("10"), year=2024, kind="expense"
    )
    assert refund.kind == "expense"


def test_transaction_category_defaults_empty() -> None:
    bare = Transaction(date=date(2025, 3, 4), label="X", amount=Decimal("1"), year=2025)
    assert bare.category == ""
    full = Transaction(
        date=date(2025, 3, 3),
        label="LIMPIEZA PORTALES",
        amount=Decimal("-10"),
        year=2025,
        category="LIMPIEZA PORTALES",
    )
    assert full.category == "LIMPIEZA PORTALES"


def test_alert_kind_members() -> None:
    assert {k.name for k in AlertKind} == {
        "SUMMARY_MISMATCH",
        "MISSING_TRANSACTION",
    }


def test_transaction_missing_defaults_false() -> None:
    t = Transaction(date(2024, 1, 10), "Cuotas", Decimal("100"), 2024)
    assert t.missing is False


def test_transaction_missing_can_be_set() -> None:
    t = Transaction(date(2024, 1, 10), "Cuotas", Decimal("100"), 2024, missing=True)
    assert t.missing is True


def test_missing_transaction_alert_kind_exists() -> None:
    assert AlertKind.MISSING_TRANSACTION.value == "missing_transaction"


def test_alert_carries_payload() -> None:
    a = Alert(kind=AlertKind.SUMMARY_MISMATCH, message="x", payload={"year": 2024})
    assert a.payload["year"] == 2024


def test_parsed_year_period_end_defaults_none() -> None:
    py = ParsedYear(
        year=2025,
        transactions=(),
        summary_income=Decimal("0"),
        summary_expense=Decimal("0"),
    )
    assert py.period_end is None
