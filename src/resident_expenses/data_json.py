"""Load the canonical JSON data files into domain types.

JSON is the source of truth for the pipeline (hand-correctable after extraction).
This module validates structure and ENFORCES the sign convention (income positive,
expense negative).
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from resident_expenses.models import ParsedYear, Transaction


class DataError(Exception):
    """Raised when a data JSON file is missing fields or malformed."""


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DataError(f"data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataError(f"{path}: invalid JSON: {exc}") from exc


def _dec(value: object, ctx: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise DataError(f"{ctx}: invalid amount {value!r}") from exc


def _parse_date(value: object, ctx: str) -> date:
    if not isinstance(value, str):
        raise DataError(f"{ctx}: date must be a string (YYYY-MM-DD)")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise DataError(f"{ctx}: invalid date {value!r}") from exc


def _optional_date(value: object, ctx: str) -> date | None:
    return None if value is None else _parse_date(value, ctx)


def _parse_transaction(raw: object, year: int, ctx: str) -> Transaction:
    if not isinstance(raw, dict):
        raise DataError(f"{ctx}: must be an object")
    # The amount's sign is the single source of truth for income vs. expense; it is
    # stored verbatim and Transaction.kind derives from it.
    amount = _dec(raw.get("amount"), f"{ctx}.amount")
    label = str(raw.get("label", ""))
    # kind defaults to the sign (the common case); it is given explicitly only for a
    # section reversal — a negative entry that still belongs to income, or vice versa.
    kind = raw.get("kind")
    if kind is not None and kind not in ("income", "expense"):
        raise DataError(f"{ctx}.kind: must be 'income' or 'expense', got {kind!r}")
    missing = raw.get("missing", False)
    if not isinstance(missing, bool):
        raise DataError(f"{ctx}.missing: must be a boolean, got {missing!r}")
    return Transaction(
        date=_parse_date(raw.get("date"), f"{ctx}.date"),
        label=label,
        amount=amount,
        year=year,
        category=str(raw.get("category") or label),  # fall back to concept
        kind=kind,
        missing=missing,
    )


def load_year(path: Path) -> ParsedYear:
    data = _read_json(path)
    if not isinstance(data, dict):
        raise DataError(f"{path}: top level must be an object")

    year = data.get("year")
    if not isinstance(year, int):
        raise DataError(f"{path}: 'year' must be an integer")

    raw_txns = data.get("transactions", [])
    if not isinstance(raw_txns, list):
        raise DataError(f"{path}: 'transactions' must be a list")
    transactions = tuple(
        _parse_transaction(t, year, f"{path}: transaction[{i}]") for i, t in enumerate(raw_txns)
    )

    summary = data.get("summary", {})
    if not isinstance(summary, dict):
        raise DataError(f"{path}: 'summary' must be an object")
    summary_income = _dec(summary.get("income", "0"), f"{path}: summary.income")
    summary_expense = _dec(summary.get("expense", "0"), f"{path}: summary.expense")
    if summary_expense > 0:
        summary_expense = -summary_expense

    return ParsedYear(
        year=year,
        transactions=transactions,
        summary_income=summary_income,
        summary_expense=summary_expense,
        period_end=_optional_date(data.get("period_end"), f"{path}: period_end"),
    )
