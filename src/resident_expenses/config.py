"""Load and validate the user's config.json (kept outside the repo)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    """Raised when config.json is missing fields or malformed."""


@dataclass(frozen=True)
class Config:
    building_name: str
    currency: str
    data_dir: Path


def _require(data: dict[str, object], key: str) -> object:
    if key not in data:
        raise ConfigError(f"config.json missing required field: {key!r}")
    return data[key]


def load_config(path: Path) -> Config:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"config.json is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("config.json must be a JSON object")

    return Config(
        building_name=str(_require(data, "building_name")),
        currency=str(data.get("currency", "EUR")),
        data_dir=Path(str(_require(data, "data_dir"))),
    )
