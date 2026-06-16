import json
from pathlib import Path

LOCALES = (
    Path(__file__).resolve().parents[2] / "src/resident_expenses/report/templates/locales.json"
)


def _keys(node: object, prefix: str = "") -> dict[str, str]:
    """Flatten nested dict keys; lists are leaves (compared by length)."""
    out: dict[str, str] = {}
    if isinstance(node, dict):
        for k, v in node.items():
            out.update(_keys(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(node, list):
        out[prefix] = f"list[{len(node)}]"
    else:
        out[prefix] = "str"
    return out


def test_locales_file_loads() -> None:
    data = json.loads(LOCALES.read_text(encoding="utf-8"))
    assert set(data) == {"es", "en"}


def test_es_en_have_identical_key_shape() -> None:
    data = json.loads(LOCALES.read_text(encoding="utf-8"))
    assert _keys(data["es"]) == _keys(data["en"])


def test_twelve_month_names_each_language() -> None:
    data = json.loads(LOCALES.read_text(encoding="utf-8"))
    assert len(data["es"]["months"]) == 12
    assert len(data["en"]["months"]) == 12
