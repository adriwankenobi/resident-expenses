from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from resident_expenses.models import (
    Alert,
    AlertKind,
    FiscalPeriod,
    ReportModel,
    Transaction,
)
from resident_expenses.report.render import render_report


def _model() -> ReportModel:
    return ReportModel(
        generated_at=date(2026, 6, 13),
        building_name="Comunidad Test",
        currency="EUR",
        years=(2025,),
        periods=(FiscalPeriod(year=2025, start=date(2025, 3, 10), end=date(2026, 1, 20)),),
        transactions=(
            Transaction(
                date(2025, 3, 10),
                "Cuotas marzo",
                Decimal("287.75"),
                2025,
                category="Cuotas ordinarias",
            ),
            Transaction(
                date(2025, 4, 15),
                "LIMPIEZA",
                Decimal("-120.00"),
                2025,
                category="LIMPIEZA",
            ),
            # Same exercise (2025), but spilling into a later calendar year — it stays
            # on the single 2025 fiscal tab.
            Transaction(
                date(2026, 1, 20),
                "Cuotas enero",
                Decimal("287.75"),
                2025,
                category="Cuotas ordinarias",
            ),
        ),
        alerts=(Alert(kind=AlertKind.SUMMARY_MISMATCH, message="drift", payload={}),),
    )


def test_render_writes_self_contained_html(tmp_path: Path) -> None:
    out = tmp_path / "report.html"
    render_report(_model(), out)
    html = out.read_text(encoding="utf-8")
    assert "Comunidad Test" in html
    assert "Plotly" in html  # plotly.js inlined
    # Tabs are fiscal exercises (one per data file), filtered by the exercise year,
    # not the calendar year — the 2025 exercise spills into 2026 but stays one tab.
    assert 'data-year="2025"' in html
    assert 'data-year="2026"' not in html
    # The tab shows a three-line label: an exercise ordinal ("YEAR n", oldest = 1)
    # over a fiscal-year heading (full years) over a day/month range.
    assert "2025 / 2026" in html
    assert "10/03 – 20/01" in html
    assert "YEAR</span> 1" in html  # the only exercise is the first
    assert 'class="tab-index"' in html
    assert 'class="tab-year"' in html
    assert 'class="tab-range"' in html
    # Summary leads with a "Days" box, styled like the others (a single number + a
    # "Days" label, no inline date range). It follows the year tab only (independent
    # of the income/expense filter), so each exercise ships its ISO start/end.
    assert 'id="kpi-days"' in html
    assert 'id="kpi-period"' not in html
    assert html.index('id="kpi-days"') < html.index('id="kpi-income"')
    assert '"start"' in html
    assert '"end"' in html
    assert "function periodFor(" in html
    # Alerts are now client-rendered into a container; the section markup is always
    # present (JS shows it only when there are alerts), and the message text is
    # localized at runtime from the payload rather than printed into static HTML.
    assert 'id="section-alerts"' in html
    assert 'id="alerts-body"' in html
    # Income and expenses each get their own section: a monthly stacked bar chart
    # plus a category-share donut (with percentages).
    assert "chart-income-monthly" in html
    assert "chart-expense-monthly" in html
    assert "chart-income-donut" in html
    assert "chart-expense-donut" in html
    assert 'id="section-income"' in html
    assert 'id="section-expense"' in html
    assert "function renderDonut(" in html
    # The transaction filter lists only categories present in the selected period.
    assert "function yearFiltered(" in html
    # Global all/income/expenses filter, styled like the year tabs.
    assert 'id="kind-tabs"' in html
    assert 'data-kind="all"' in html
    assert 'data-kind="income"' in html
    assert 'data-kind="expense"' in html
    # Double-click isolates a category in both the table-filter pills and the
    # Plotly chart legend; single-click stays a plain toggle.
    assert "function isolate(" in html
    assert "plotly_legenddoubleclick" in html
    assert "'dblclick'" in html


def test_tabs_number_exercises_oldest_first(tmp_path: Path) -> None:
    # Two exercises, newest-first as the model delivers them. The oldest is YEAR 1
    # and the count increases forward in time, so the newer (leftmost) tab is YEAR 2.
    model = ReportModel(
        generated_at=date(2026, 6, 13),
        building_name="Casa",
        currency="EUR",
        years=(2025, 2024),
        periods=(
            FiscalPeriod(year=2025, start=date(2024, 10, 1), end=date(2025, 9, 30)),
            FiscalPeriod(year=2024, start=date(2023, 10, 1), end=date(2024, 9, 30)),
        ),
        transactions=(
            Transaction(date(2024, 10, 5), "A", Decimal("10.00"), 2025, category="X"),
            Transaction(date(2023, 10, 5), "B", Decimal("10.00"), 2024, category="X"),
        ),
        alerts=(),
    )
    out = tmp_path / "report.html"
    render_report(model, out)
    html = out.read_text(encoding="utf-8")
    assert "YEAR</span> 1" in html and "YEAR</span> 2" in html
    # Tabs render newest-first, so YEAR 2 (the 2025 exercise) precedes YEAR 1.
    assert html.index("YEAR</span> 2") < html.index("YEAR</span> 1")


def test_alerts_section_hidden_when_no_alerts(tmp_path: Path) -> None:
    # The Alerts section markup is always present (client-rendered), but it is hidden
    # by default and JS keeps it hidden when an exercise reconciles cleanly.
    model = _model()
    model = replace(model, alerts=())
    out = tmp_path / "report.html"
    render_report(model, out)
    html = out.read_text(encoding="utf-8")
    assert 'id="section-alerts" style="display:none"' in html


def test_report_embeds_locale_blob_and_alert_payload(tmp_path: Path) -> None:
    import json

    model = ReportModel(
        generated_at=date(2024, 4, 1),
        building_name="Test Bldg",
        currency="EUR",
        years=(2024,),
        periods=(FiscalPeriod(year=2024, start=date(2024, 1, 1), end=date(2024, 3, 31)),),
        transactions=(
            Transaction(
                date=date(2024, 1, 15),
                label="x",
                amount=Decimal("100"),
                year=2024,
                category="ORDINARIA",
            ),
        ),
        alerts=(
            Alert(
                kind=AlertKind.MISSING_TRANSACTION,
                message="en msg",
                payload={
                    "year": 2024,
                    "date": "2024-01-15",
                    "label": "x",
                    "amount": "100",
                    "kind": "income",
                },
            ),
        ),
    )
    out = tmp_path / "report.html"
    render_report(model, out)
    html = out.read_text(encoding="utf-8")

    # locale blob present and parseable
    assert 'id="locale-data"' in html
    start = html.index('id="locale-data"')
    blob = html[html.index(">", start) + 1 : html.index("</script>", start)]
    locales = json.loads(blob)
    assert set(locales) == {"es", "en"}

    # alert payload is carried into the data blob
    dstart = html.index('id="model-data"')
    dblob = html[html.index(">", dstart) + 1 : html.index("</script>", dstart)]
    data = json.loads(dblob)
    assert data["alerts"][0]["payload"]["date"] == "2024-01-15"


def test_report_has_i18n_markers_and_language_control(tmp_path: Path) -> None:
    model = ReportModel(
        generated_at=date(2024, 4, 1),
        building_name="B",
        currency="EUR",
        years=(2024,),
        periods=(FiscalPeriod(year=2024, start=date(2024, 1, 1), end=date(2024, 3, 31)),),
        transactions=(
            Transaction(
                date=date(2024, 1, 15),
                label="x",
                amount=Decimal("100"),
                year=2024,
                category="ORDINARIA",
            ),
        ),
        alerts=(),
    )
    out = tmp_path / "report.html"
    render_report(model, out)
    html = out.read_text(encoding="utf-8")

    assert 'data-i18n="ui.summary"' in html
    assert 'data-i18n="ui.col_concept"' in html
    assert 'id="lang-tabs"' in html
    assert 'data-lang="es"' in html and 'data-lang="en"' in html


def test_alerts_rendered_from_container_not_jinja(tmp_path: Path) -> None:
    model = ReportModel(
        generated_at=date(2024, 4, 1),
        building_name="B",
        currency="EUR",
        years=(2024,),
        periods=(FiscalPeriod(year=2024, start=date(2024, 1, 1), end=date(2024, 3, 31)),),
        transactions=(
            Transaction(
                date=date(2024, 1, 15),
                label="x",
                amount=Decimal("100"),
                year=2024,
                category="ORDINARIA",
            ),
        ),
        alerts=(
            Alert(
                kind=AlertKind.SUMMARY_MISMATCH,
                message="en msg",
                payload={
                    "year": 2024,
                    "field": "income",
                    "computed": "100",
                    "summary": "200",
                },
            ),
        ),
    )
    out = tmp_path / "report.html"
    render_report(model, out)
    html = out.read_text(encoding="utf-8")

    # Alert messages render client-side from the payload, not baked into the static HTML.
    assert "en msg" not in html
    # A JS container exists for client-rendered alerts.
    assert 'id="alerts-body"' in html


def test_report_has_row_flash_style(tmp_path: Path) -> None:
    model = ReportModel(
        generated_at=date(2024, 4, 1),
        building_name="B",
        currency="EUR",
        years=(2024,),
        periods=(FiscalPeriod(year=2024, start=date(2024, 1, 1), end=date(2024, 3, 31)),),
        transactions=(
            Transaction(
                date=date(2024, 1, 15),
                label="x",
                amount=Decimal("100"),
                year=2024,
                category="ORDINARIA",
            ),
        ),
        alerts=(),
    )
    out = tmp_path / "report.html"
    render_report(model, out)
    html = out.read_text(encoding="utf-8")
    assert "row-flash" in html


def test_render_carries_missing_flag(tmp_path: Path) -> None:
    model = _model()
    flagged = replace(model.transactions[0], missing=True)
    model = replace(
        model,
        transactions=(flagged,) + model.transactions[1:],
        alerts=(
            Alert(
                kind=AlertKind.MISSING_TRANSACTION,
                message="drift",
                payload={
                    "year": 2025,
                    "date": "2025-03-10",
                    "label": "Cuotas marzo",
                    "amount": "287.75",
                    "kind": "income",
                },
            ),
        ),
    )
    out = tmp_path / "report.html"
    render_report(model, out)
    html = out.read_text(encoding="utf-8")
    assert '"missing": true' in html
    assert "missing_transaction" in html


def test_template_has_missing_rendering(tmp_path: Path) -> None:
    out = tmp_path / "report.html"
    render_report(_model(), out)
    html = out.read_text(encoding="utf-8")
    # CSS class for the muted/italic flagged row
    assert "txn-missing" in html
    # alertMessage handles the new kind
    assert "missing_transaction" in html
    # badge uses the localized tooltip key
    assert "missing_badge_title" in html


def _balances_from_html(html: str) -> dict[str, str]:
    import json

    dstart = html.index('id="model-data"')
    dblob = html[html.index(">", dstart) + 1 : html.index("</script>", dstart)]
    data = json.loads(dblob)
    return {t["label"]: t["balance"] for t in data["transactions"]}


def test_balance_column_header_present(tmp_path: Path) -> None:
    out = tmp_path / "report.html"
    render_report(_model(), out)
    html = out.read_text(encoding="utf-8")
    assert 'data-i18n="ui.col_balance"' in html


def test_running_balance_accumulates_chronologically(tmp_path: Path) -> None:
    # Input given out of date order, to prove the balance accumulates by date (not by
    # array order) yet is stored per row so each label keeps its own fixed balance.
    model = ReportModel(
        generated_at=date(2026, 6, 13),
        building_name="Bal",
        currency="EUR",
        years=(2025,),
        periods=(FiscalPeriod(year=2025, start=date(2025, 1, 1), end=date(2025, 12, 31)),),
        transactions=(
            Transaction(date(2025, 6, 1), "mid", Decimal("-30.00"), 2025, category="C"),
            Transaction(date(2025, 1, 1), "first", Decimal("100.00"), 2025, category="C"),
            Transaction(date(2025, 12, 1), "last", Decimal("50.00"), 2025, category="C"),
        ),
        alerts=(),
    )
    out = tmp_path / "report.html"
    render_report(model, out)
    balances = _balances_from_html(out.read_text(encoding="utf-8"))
    # 100 → 100 - 30 = 70 → 70 + 50 = 120, assigned by date regardless of input order.
    assert balances == {"first": "100.00", "mid": "70.00", "last": "120.00"}


def _txns_from_html(html: str) -> list[dict[str, Any]]:
    import json

    dstart = html.index('id="model-data"')
    dblob = html[html.index(">", dstart) + 1 : html.index("</script>", dstart)]
    txns: list[dict[str, Any]] = json.loads(dblob)["transactions"]
    return txns


def test_same_day_balance_follows_data_source_order(tmp_path: Path) -> None:
    # Three transactions share a date; the running balance must accumulate them in
    # data-source (array) order, and each row gets a chronological seq the table sorts
    # by descending so the last same-day row ends at the running total.
    model = ReportModel(
        generated_at=date(2026, 6, 13),
        building_name="Seq",
        currency="EUR",
        years=(2025,),
        periods=(FiscalPeriod(year=2025, start=date(2025, 1, 1), end=date(2025, 12, 31)),),
        transactions=(
            Transaction(date(2025, 1, 1), "open", Decimal("1000.00"), 2025, category="C"),
            Transaction(date(2025, 6, 5), "a", Decimal("-100.00"), 2025, category="C"),
            Transaction(date(2025, 6, 5), "b", Decimal("-30.00"), 2025, category="C"),
            Transaction(date(2025, 6, 5), "c", Decimal("-20.00"), 2025, category="C"),
        ),
        alerts=(),
    )
    out = tmp_path / "report.html"
    render_report(model, out)
    txns = {t["label"]: t for t in _txns_from_html(out.read_text(encoding="utf-8"))}
    # Same-day rows accumulate in data-source order: 1000 → 900 → 870 → 850.
    assert txns["a"]["balance"] == "900.00"
    assert txns["b"]["balance"] == "870.00"
    assert txns["c"]["balance"] == "850.00"
    # seq is strictly increasing in data-source order for the tied day; the last same-
    # day row carries the final total and the highest seq (top of the sorted table).
    assert txns["open"]["seq"] < txns["a"]["seq"] < txns["b"]["seq"] < txns["c"]["seq"]
    # The table sorts by seq descending, not the date string.
    assert "b.seq - a.seq" in out.read_text(encoding="utf-8")


def test_render_handles_empty_years(tmp_path: Path) -> None:
    model = ReportModel(
        generated_at=date(2026, 6, 13),
        building_name="Empty",
        currency="EUR",
        years=(),
        periods=(),
        transactions=(),
        alerts=(),
    )
    out = tmp_path / "report.html"
    render_report(model, out)
    assert "Empty" in out.read_text(encoding="utf-8")
