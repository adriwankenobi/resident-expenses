import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from resident_expenses.data_json import DataError, load_year


def _write(tmp_path: Path, name: str, data: dict[str, Any]) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _year_doc() -> dict[str, Any]:
    return {
        "year": 2024,
        "transactions": [
            {"date": "2024-01-10", "label": "Cuotas enero", "amount": "287.75"},
            {"date": "2024-02-15", "label": "Calefacción", "amount": "-120.00"},
        ],
        "summary": {"income": "287.75", "expense": "-120.00"},
    }


def test_load_year_happy_path(tmp_path: Path) -> None:
    py = load_year(_write(tmp_path, "2024.json", _year_doc()))
    assert py.year == 2024
    assert len(py.transactions) == 2
    assert py.transactions[0].kind == "income"
    assert py.transactions[0].amount == Decimal("287.75")
    assert py.transactions[0].date == date(2024, 1, 10)
    assert py.transactions[0].year == 2024
    assert py.transactions[1].amount == Decimal("-120.00")
    assert py.summary_income == Decimal("287.75")
    assert py.summary_expense == Decimal("-120.00")


def test_amount_sign_determines_kind(tmp_path: Path) -> None:
    # Sign is the single source of truth: amount is stored verbatim, kind derives from it.
    py = load_year(_write(tmp_path, "2024.json", _year_doc()))
    assert py.transactions[0].kind == "income"  # +287.75
    assert py.transactions[1].kind == "expense"  # -120.00


def test_negative_amount_is_expense(tmp_path: Path) -> None:
    doc = _year_doc()
    doc["transactions"][0]["amount"] = "-10.00"  # was "income" shape; sign now wins
    py = load_year(_write(tmp_path, "2024.json", doc))
    assert py.transactions[0].amount == Decimal("-10.00")
    assert py.transactions[0].kind == "expense"


def test_explicit_kind_overrides_sign(tmp_path: Path) -> None:
    # A negative entry inside the income section (a reversal) carries kind explicitly,
    # so it stays income despite the negative sign.
    doc = _year_doc()
    doc["transactions"][1]["kind"] = "income"  # the -120.00 row
    py = load_year(_write(tmp_path, "2024.json", doc))
    assert py.transactions[1].amount == Decimal("-120.00")
    assert py.transactions[1].kind == "income"


def test_invalid_kind_raises(tmp_path: Path) -> None:
    doc = _year_doc()
    doc["transactions"][0]["kind"] = "revenue"
    with pytest.raises(DataError):
        load_year(_write(tmp_path, "2024.json", doc))


def test_positive_summary_expense_is_negated(tmp_path: Path) -> None:
    doc = _year_doc()
    doc["summary"]["expense"] = "120.00"
    py = load_year(_write(tmp_path, "2024.json", doc))
    assert py.summary_expense == Decimal("-120.00")


def test_category_read_with_fallback(tmp_path: Path) -> None:
    doc = _year_doc()
    doc["transactions"][0]["category"] = "Cuotas"  # explicit
    # transaction[1] has no category -> falls back to its concept (label)
    py = load_year(_write(tmp_path, "2024.json", doc))
    assert py.transactions[0].category == "Cuotas"
    assert py.transactions[1].category == py.transactions[1].label


def test_reads_period_end(tmp_path: Path) -> None:
    doc = _year_doc()
    doc["period_end"] = "2025-02-28"
    py = load_year(_write(tmp_path, "2024.json", doc))
    assert py.period_end == date(2025, 2, 28)


def test_period_end_defaults_none(tmp_path: Path) -> None:
    py = load_year(_write(tmp_path, "2024.json", _year_doc()))
    assert py.period_end is None


def test_bad_date_raises(tmp_path: Path) -> None:
    doc = _year_doc()
    doc["transactions"][0]["date"] = "10/01/2024"
    with pytest.raises(DataError):
        load_year(_write(tmp_path, "2024.json", doc))


def test_missing_year_raises(tmp_path: Path) -> None:
    doc = _year_doc()
    del doc["year"]
    with pytest.raises(DataError):
        load_year(_write(tmp_path, "2024.json", doc))


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(DataError):
        load_year(tmp_path / "nope.json")


def test_missing_defaults_false(tmp_path: Path) -> None:
    py = load_year(_write(tmp_path, "2024.json", _year_doc()))
    assert all(t.missing is False for t in py.transactions)


def test_missing_true_parses(tmp_path: Path) -> None:
    doc = _year_doc()
    doc["transactions"][0]["missing"] = True
    py = load_year(_write(tmp_path, "2024.json", doc))
    assert py.transactions[0].missing is True
    assert py.transactions[1].missing is False


def test_missing_non_boolean_raises(tmp_path: Path) -> None:
    doc = _year_doc()
    doc["transactions"][0]["missing"] = "yes"
    with pytest.raises(DataError, match="missing"):
        load_year(_write(tmp_path, "2024.json", doc))
