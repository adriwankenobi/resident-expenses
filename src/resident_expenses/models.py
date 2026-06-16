"""Frozen domain dataclasses and enums. No I/O lives here."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Literal

Kind = Literal["income", "expense"]


class AlertKind(Enum):
    SUMMARY_MISMATCH = "summary_mismatch"
    MISSING_TRANSACTION = "missing_transaction"


@dataclass(frozen=True)
class Transaction:
    date: date
    label: str
    amount: Decimal  # positive for income, negative for expense
    year: int
    # Display/grouping category (the concept text). Assigned by the data source;
    # the core treats it as opaque.
    category: str = ""
    # Income vs. expense follows the ledger SECTION, not just the amount's sign: a
    # reversal inside the income section (e.g. a refund) is negative yet still income.
    # Defaults to the sign — the common case — when the source doesn't specify it.
    kind: Kind | None = None
    # Recorded in the ledger but never actually occurred (e.g. income that never
    # arrived). Informational only — the amount still counts toward totals; this drives
    # an alert and a row marker in the report.
    missing: bool = False

    def __post_init__(self) -> None:
        if self.kind is None:
            object.__setattr__(self, "kind", "income" if self.amount >= 0 else "expense")


@dataclass(frozen=True)
class ParsedYear:
    year: int
    transactions: tuple[Transaction, ...]
    summary_income: Decimal
    summary_expense: Decimal  # negative
    # Exercise end; sets the fiscal period's display window. Falls back to the
    # latest transaction date when absent.
    period_end: date | None = None


@dataclass(frozen=True)
class FiscalPeriod:
    """A fiscal exercise's display window: its year and the date range it covers.

    ``start`` is the exercise's first transaction date; ``end`` is its explicit
    exercise end (``ParsedYear.period_end``) or the last transaction date."""

    year: int
    start: date
    end: date


@dataclass(frozen=True)
class Alert:
    kind: AlertKind
    message: str
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ReportModel:
    generated_at: date
    building_name: str
    currency: str
    years: tuple[int, ...]
    periods: tuple[FiscalPeriod, ...]
    transactions: tuple[Transaction, ...]
    alerts: tuple[Alert, ...]
