from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml

from packages.common.config import settings


def load_routes() -> dict:
    p = Path(settings.routes_path)
    if not p.exists():
        return {"default": {"model": "rules-only", "max_cost": 0.0}}
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def choose_route(contract: str, budgets: dict[str, float] | None = None) -> dict:
    routes = load_routes()
    route = routes.get(contract) or routes.get("default") or {"model": "rules-only"}
    meta = {
        "chosen_model": route.get("model", "rules-only"),
        "budgets": budgets or {},
        "route": route,
    }
    return meta
