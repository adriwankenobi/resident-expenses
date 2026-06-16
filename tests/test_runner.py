import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from resident_expenses.models import ParsedYear, Transaction
from resident_expenses.runner import run_report, run_report_from_data


def _py(year: int) -> ParsedYear:
    # One cuota in January, flagged as recorded-but-missing so the
    # missing-transaction check fires one alert.
    return ParsedYear(
        year=year,
        transactions=(
            Transaction(
                date(year, 1, 10),
                "Cuotas enero",
                Decimal("60.00"),
                year,
                category="Cuotas ordinarias",
                missing=True,
            ),
        ),
        summary_income=Decimal("60.00"),
        summary_expense=Decimal("0"),
        period_end=date(year, 3, 31),
    )


def test_run_report_from_data_writes_html(tmp_path: Path) -> None:
    out = tmp_path / "report.html"
    summary = run_report_from_data(
        parsed_years=[_py(2024), _py(2025)],
        building_name="Casa",
        currency="EUR",
        output_path=out,
        today=date(2026, 6, 13),
    )
    assert out.exists()
    assert summary["years"] == 2
    assert summary["alerts"] > 0  # the missing-flagged cuota fires one alert per year


def test_run_report_reads_json_dir(tmp_path: Path) -> None:
    from resident_expenses.config import Config

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for year in (2024, 2025):
        (data_dir / f"{year}.json").write_text(
            json.dumps(
                {
                    "year": year,
                    "transactions": [
                        {
                            "date": f"{year}-01-10",
                            "label": "Cuotas enero",
                            "amount": "60.00",
                        }
                    ],
                    "summary": {"income": "60.00", "expense": "0"},
                }
            ),
            encoding="utf-8",
        )
    # A non-year JSON in the same dir must be ignored by the year glob.
    (data_dir / "metadata.json").write_text(json.dumps({"note": "ignored"}), encoding="utf-8")

    cfg = Config(
        building_name="Casa",
        currency="EUR",
        data_dir=data_dir,
    )
    out = tmp_path / "report.html"
    summary = run_report(cfg, out, today=date(2026, 6, 13))
    assert out.exists()
    assert summary["years"] == 2  # the non-year JSON is NOT counted as a year file
