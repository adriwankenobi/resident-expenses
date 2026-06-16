import json
from pathlib import Path

import pytest

from resident_expenses.config import ConfigError, load_config


def _write(tmp_path: Path, data: dict[str, object]) -> Path:
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_full_config(tmp_path: Path) -> None:
    cfg = load_config(
        _write(
            tmp_path,
            {
                "building_name": "Casa",
                "currency": "EUR",
                "data_dir": str(tmp_path / "data"),
            },
        )
    )
    assert cfg.building_name == "Casa"
    assert cfg.currency == "EUR"
    assert cfg.data_dir == tmp_path / "data"


def test_currency_defaults_to_eur(tmp_path: Path) -> None:
    cfg = load_config(
        _write(
            tmp_path,
            {
                "building_name": "Casa",
                "data_dir": str(tmp_path),
            },
        )
    )
    assert cfg.currency == "EUR"


def test_missing_required_field_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, {"currency": "EUR"}))
