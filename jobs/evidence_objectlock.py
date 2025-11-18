from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable

from apps.common.s3_adapter import select_adapter
from apps.obs.evidence.indexer import write_index

EVIDENCE_DIR = os.getenv("DECISIONOS_EVIDENCE_DIR", "var/evidence")
EVIDENCE_INDEX = os.getenv("DECISIONOS_EVIDENCE_INDEX", os.path.join(EVIDENCE_DIR, "index.json"))
REPORT_PATH = os.getenv("DECISIONOS_OBJECTLOCK_REPORT", os.path.join(EVIDENCE_DIR, "objectlock-report.json"))


def _load_index() -> Dict[str, Any]:
    write_index(EVIDENCE_DIR, EVIDENCE_INDEX)  # ensure fresh index
    with Path(EVIDENCE_INDEX).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _index_items(index: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    items = index.get("items")
    if isinstance(items, list):
        for entry in items:
            yield entry
        return

    files = index.get("files")
    if isinstance(files, list):
        for entry in files:
            # back-compat: convert to new-ish shape
            data = dict(entry)
            path = data.get("path") or ""
            if not os.path.isabs(path):
                path = os.path.join(index.get("root") or EVIDENCE_DIR, path)
            yield {
                "path": path,
                "tier": (data.get("tier") or "WIP").upper(),
                "tampered": bool(data.get("tampered")),
                "sha256": data.get("sha256"),
                "created_at": data.get("generated_at"),
                "locked_at": data.get("locked_at"),
            }


def _read_bytes(path: str) -> bytes:
    return Path(path).read_bytes()


def main() -> None:
    index = _load_index()
    adapter = select_adapter()

    bucket = os.getenv("DECISIONOS_S3_BUCKET", "decisionos-evidence")
    prefix = (os.getenv("DECISIONOS_S3_PREFIX", "evidence/") or "").lstrip("/")
    only_locked = os.getenv("DECISIONOS_S3_UPLOAD_ONLY_LOCKED", "1") == "1"
    dry_run = os.getenv("DECISIONOS_S3_DRY_RUN", "1") == "1"
    lock_mode = os.getenv("DECISIONOS_S3_OBJECTLOCK_MODE", "GOVERNANCE").upper()
    retention_days = int(os.getenv("DECISIONOS_S3_OBJECTLOCK_RETENTION_DAYS", "30"))

    uploaded, skipped, failed = [], [], []
    for entry in _index_items(index):
        path = entry.get("path")
        if not path:
            continue
        tier = (entry.get("tier") or "WIP").upper()
        tampered = bool(entry.get("tampered"))
        if tampered:
            skipped.append({"path": path, "reason": "tampered"})
            continue
        if only_locked and tier != "LOCKED":
            skipped.append({"path": path, "reason": "not_locked"})
            continue

        key = f"{prefix}{os.path.basename(path)}"
        if dry_run:
            uploaded.append({"path": path, "bucket": bucket, "key": key, "dry_run": True})
            continue

        try:
            payload = _read_bytes(path)
            resp = adapter.put_with_object_lock(bucket, key, payload, lock_mode=lock_mode, retention_days=retention_days)
            uploaded.append({"path": path, "bucket": bucket, "key": key, "resp": resp.extra, "adapter": resp.adapter})
        except Exception as exc:  # pragma: no cover - defensive
            failed.append({"path": path, "error": str(exc)})

    report = {
        "mode": os.getenv("DECISIONOS_S3_MODE", "stub"),
        "bucket": bucket,
        "prefix": prefix,
        "policy": {
            "only_locked": only_locked,
            "dry_run": dry_run,
            "lock_mode": lock_mode,
            "retention_days": retention_days,
        },
        "counts": {"uploaded": len(uploaded), "skipped": len(skipped), "failed": len(failed)},
        "uploaded": uploaded,
        "skipped": skipped,
        "failed": failed,
    }
    report_path = Path(REPORT_PATH)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"[objectlock] mode={report['mode']} uploaded={len(uploaded)} skipped={len(skipped)} "
        f"failed={len(failed)} -> {report_path}"
    )


if __name__ == "__main__":
    main()
