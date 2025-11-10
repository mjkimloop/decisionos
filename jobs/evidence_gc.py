from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Dict, List

from apps.obs.evidence.gc_config import load_gc_cfg
from apps.obs.evidence.indexer import scan_dir

TENANT_UNKNOWN = "__global__"


def _parse_mtime(entry: Dict[str, str]) -> datetime:
    try:
        return datetime.fromisoformat(entry["mtime"].replace("Z", "+00:00"))
    except Exception:
        return datetime.fromtimestamp(0, tz=timezone.utc)


def _tenant(entry: Dict[str, str]) -> str:
    return entry.get("tenant") or TENANT_UNKNOWN


def run(root: str = "var/evidence", dry_run: bool | None = None) -> List[str]:
    cfg = load_gc_cfg()
    if dry_run is None:
        dry_run = cfg.dry_run
    index = scan_dir(root)
    files = sorted(index["files"], key=lambda f: _parse_mtime(f))
    now = datetime.now(timezone.utc)

    tenant_counts: Dict[str, int] = {}
    for f in files:
        tenant_counts[_tenant(f)] = tenant_counts.get(_tenant(f), 0) + 1

    deleted_counts: Dict[str, int] = {}
    candidates: List[str] = []
    for f in files:
        tier = f.get("tier", "WIP")
        if tier == "LOCKED":
            continue
        if any(fnmatch(f["path"], pattern) for pattern in cfg.exclude_globs):
            continue
        retention = cfg.retention_days.get(tier, cfg.retention_days.get("WIP", 7))
        if _parse_mtime(f) > now - timedelta(days=retention):
            continue
        tenant = _tenant(f)
        remaining = tenant_counts[tenant] - deleted_counts.get(tenant, 0)
        if remaining <= cfg.keep_min_per_tenant:
            continue
        candidates.append(f["path"])
        deleted_counts[tenant] = deleted_counts.get(tenant, 0) + 1

    if dry_run:
        print(json.dumps({"delete_candidates": candidates}, ensure_ascii=False, indent=2))
        return candidates

    for name in candidates:
        try:
            Path(root, name).unlink()
            print(f"[gc] deleted {name}")
        except FileNotFoundError:
            continue
    return candidates


def main() -> None:
    run()


if __name__ == "__main__":
    main()
