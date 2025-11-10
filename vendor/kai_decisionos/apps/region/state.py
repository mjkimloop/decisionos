from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from packages.common.config import settings


@dataclass
class RegionStatus:
    active: str
    secondary: Optional[str]
    from_config: bool


def _config_path() -> Path:
    # try configured path; fallback to repo base
    p = Path(settings.region_config_path)
    if p.exists():
        return p
    base = Path(__file__).resolve().parents[2]
    q = base / settings.region_config_path
    return q


def _load_config() -> dict:
    p = _config_path()
    if p.exists():
        try:
            return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}
    return {}


def status() -> RegionStatus:
    cfg = _load_config()
    active = cfg.get("active_region", settings.active_region)
    secondary = cfg.get("secondary_region", settings.secondary_region)
    return RegionStatus(active=active, secondary=secondary, from_config=bool(cfg))


def set_active(new_region: str) -> RegionStatus:
    p = _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    cfg = _load_config()
    cfg["active_region"] = new_region
    if "secondary_region" not in cfg:
        cfg["secondary_region"] = settings.secondary_region
    p.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return status()
