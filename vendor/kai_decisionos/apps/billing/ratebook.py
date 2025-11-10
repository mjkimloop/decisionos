from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml


DEFAULT_RATEBOOK_PATH = Path("config/ratebook.yaml")

_FALLBACK_RATEBOOK: Dict[str, Dict[str, Any]] = {
    "trial": {
        "decision_calls": 0.0,
        "storage_gb_month": 0.0,
    },
    "growth": {
        "decision_calls": 0.002,
        "storage_gb_month": 0.08,
    },
    "enterprise": {
        "decision_calls": 0.0015,
        "storage_gb_month": 0.06,
    },
}


def _read_file(path: Path) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        return _FALLBACK_RATEBOOK
    data: Dict[str, Dict[str, Any]]
    if path.suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
    return data or _FALLBACK_RATEBOOK


@lru_cache(maxsize=4)
def load_ratebook(path: Path | None = None) -> Dict[str, Dict[str, Any]]:
    target = path or DEFAULT_RATEBOOK_PATH
    return _read_file(target)


def get_unit_price(plan: str, metric: str, default: float = 0.0, *, path: Path | None = None) -> float:
    ratebook = load_ratebook(path)
    plan_rates = ratebook.get(plan) or ratebook.get("trial") or {}
    return float(plan_rates.get(metric, default))


def list_plans(path: Path | None = None) -> Dict[str, Dict[str, Any]]:
    return load_ratebook(path)


def clear_cache() -> None:
    load_ratebook.cache_clear()


__all__ = ["DEFAULT_RATEBOOK_PATH", "load_ratebook", "get_unit_price", "list_plans", "clear_cache"]

