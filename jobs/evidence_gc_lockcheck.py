from __future__ import annotations

import glob
import json
import os
import time
from typing import Dict, List

try:
    import boto3  # type: ignore
except Exception:  # pragma: no cover
    boto3 = None

RETENTION_WIP_DAYS = int(os.getenv("DECISIONOS_WIP_RETENTION_DAYS", "3"))


def load_index(directory: str) -> List[Dict]:
    rows: List[Dict] = []
    for path in glob.glob(os.path.join(directory, "*.json")):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            rows.append({"path": path, "tier": data.get("tier", "WIP"), "meta": data.get("meta", {})})
        except Exception:
            continue
    return rows


def run(directory: str, *, s3_uri: str | None = None, dry_run: bool = True) -> Dict:
    index = load_index(directory)
    now = time.time()
    expired: List[str] = []
    for row in index:
        tier = row.get("tier", "WIP")
        generated = row.get("meta", {}).get("generated_at")
        try:
            ts = time.strptime((generated or "1970-01-01T00:00:00").replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
            age_days = (now - time.mktime(ts)) / 86400.0
        except Exception:
            age_days = 999
        if tier == "WIP" and age_days > RETENTION_WIP_DAYS:
            expired.append(row["path"])
    if not dry_run:
        for path in expired:
            try:
                os.remove(path)
            except Exception:
                continue
    # S3 ObjectLock 점검 스켈레톤: 실제 구현에서는 boto3로 검사
    return {"scanned": len(index), "expired": len(expired), "dry_run": dry_run}


if __name__ == "__main__":
    out = run("var/evidence", dry_run=True)
    print(json.dumps(out, ensure_ascii=False, indent=2))
