from datetime import date
from decimal import Decimal

from resident_expenses.models import Alert, AlertKind, ParsedYear, Transaction
from resident_expenses.report.model import build_report_model


def _py(year: int) -> ParsedYear:
    return ParsedYear(
        year=year,
        transactions=(
            Transaction(date(year, 1, 10), "Cuotas enero", Decimal("287.75"), year),
            Transaction(date(year, 2, 15), "Calefacción", Decimal("-120.00"), year),
        ),
        summary_income=Decimal("287.75"),
        summary_expense=Decimal("-120.00"),
    )


def test_builds_years_descending_and_flattens_transactions() -> None:
    model = build_report_model(
        parsed_years=[_py(2024), _py(2025)],
        building_name="Casa",
        currency="EUR",
        generated_at=date(2026, 6, 13),
    )
    assert model.years == (2025, 2024)
    assert model.building_name == "Casa"
    assert len(model.transactions) == 4


def test_alerts_are_carried_through() -> None:
    model = build_report_model(
        parsed_years=[_py(2025)],
        building_name="Casa",
        currency="EUR",
        generated_at=date(2026, 6, 13),
        alerts=[Alert(kind=AlertKind.SUMMARY_MISMATCH, message="drift")],
    )
    assert len(model.alerts) == 1
    assert model.alerts[0].message == "drift"


def test_periods_span_first_to_last_transaction() -> None:
    # A fiscal exercise that opens in late 2023 and closes in Feb 2024.
    fiscal = ParsedYear(
        year=2024,
        transactions=(
            Transaction(date(2023, 10, 5), "Apertura", Decimal("100.00"), 2024),
            Transaction(date(2024, 2, 28), "Cierre", Decimal("-50.00"), 2024),
        ),
        summary_income=Decimal("100.00"),
        summary_expense=Decimal("-50.00"),
    )
    model = build_report_model(
        parsed_years=[fiscal],
        building_name="Casa",
        currency="EUR",
        generated_at=date(2026, 6, 13),
    )
    assert len(model.periods) == 1
    period = model.periods[0]
    assert period.year == 2024
    assert period.start == date(2023, 10, 5)
    assert period.end == date(2024, 2, 28)


def test_period_end_uses_explicit_exercise_end_when_present() -> None:
    fiscal = ParsedYear(
        year=2024,
        transactions=(
            Transaction(date(2023, 10, 5), "Apertura", Decimal("100.00"), 2024),
            Transaction(date(2024, 2, 28), "Cierre", Decimal("-50.00"), 2024),
        ),
        summary_income=Decimal("100.00"),
        summary_expense=Decimal("-50.00"),
        period_end=date(2024, 3, 31),
    )
    model = build_report_model(
        parsed_years=[fiscal],
        building_name="Casa",
        currency="EUR",
        generated_at=date(2026, 6, 13),
    )
    assert model.periods[0].end == date(2024, 3, 31)


def test_period_start_follows_previous_period_end() -> None:
    # Fiscal exercises are contiguous: each begins the day after the prior one
    # closed. The first transaction usually lands a few days in, so the displayed
    # start must come from the previous period's end, not the earliest txn date.
    first = ParsedYear(
        year=2024,
        transactions=(
            Transaction(date(2023, 10, 3), "Apertura", Decimal("100.00"), 2024),
            Transaction(date(2024, 9, 20), "Cierre", Decimal("-50.00"), 2024),
        ),
        summary_income=Decimal("100.00"),
        summary_expense=Decimal("-50.00"),
        period_end=date(2024, 9, 30),
    )
    second = ParsedYear(
        year=2025,
        transactions=(
            Transaction(date(2024, 10, 5), "Apertura", Decimal("100.00"), 2025),
            Transaction(date(2025, 9, 20), "Cierre", Decimal("-50.00"), 2025),
        ),
        summary_income=Decimal("100.00"),
        summary_expense=Decimal("-50.00"),
        period_end=date(2025, 9, 30),
    )
    model = build_report_model(
        parsed_years=[second, first],
        building_name="Casa",
        currency="EUR",
        generated_at=date(2026, 6, 13),
    )
    by_year = {p.year: p for p in model.periods}
    # Earliest exercise has no predecessor → keeps its first transaction date.
    assert by_year[2024].start == date(2023, 10, 3)
    # Next exercise begins the day after the prior one ended, not at its first txn.
    assert by_year[2025].start == date(2024, 10, 1)


def test_periods_are_ordered_descending_by_year() -> None:
    model = build_report_model(
        parsed_years=[_py(2024), _py(2025)],
        building_name="Casa",
        currency="EUR",
        generated_at=date(2026, 6, 13),
    )
    assert [p.year for p in model.periods] == [2025, 2024]
