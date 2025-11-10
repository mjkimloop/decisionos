from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError
import yaml


class ObjectLockCfg(BaseModel):
    enabled: bool = True
    retention_days: int = 365
    s3_bucket: Optional[str] = None
    s3_prefix: Optional[str] = None


class GCCfg(BaseModel):
    retention_days: Dict[str, int] = Field(default_factory=lambda: {"WIP": 7, "LOCKED": 365})
    keep_min_per_tenant: int = 5
    exclude_globs: List[str] = Field(default_factory=lambda: ["**/*locked.json"])
    dry_run: bool = True
    object_lock: ObjectLockCfg = ObjectLockCfg()


CONFIG_ENV = "DECISIONOS_GC_CONFIG"
DEFAULT_CONFIG = "configs/evidence/gc.yaml"


def load_gc_cfg(path: str | None = None) -> GCCfg:
    config_path = Path(path or os.getenv(CONFIG_ENV, DEFAULT_CONFIG))
    if not config_path.exists():
        return GCCfg()
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    try:
        return GCCfg(**data)
    except ValidationError as exc:
        print(f"[gc-config] invalid config -> using defaults: {exc}")
        return GCCfg()
