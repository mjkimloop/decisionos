from __future__ import annotations

import hashlib
import json
import os
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List

from apps.common.s3_adapter import select_adapter


def _sha256_bytes(blob: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(blob)
    return digest.hexdigest()


def _load_policy(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _index_hash_map(index_path: Path) -> Dict[str, str]:
    if not index_path.exists():
        return {}
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    mapping: Dict[str, str] = {}
    for field in ("items", "files"):
        entries = data.get(field)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            path = entry.get("path")
            if not path:
                continue
            name = Path(path).name
            sha = (
                entry.get("sha256")
                or entry.get("sha")
                or entry.get("signature")
                or entry.get("integrity_signature")
                or entry.get("integrity", {}).get("signature_sha256")
            )
            if isinstance(sha, str):
                mapping[name] = sha
    return mapping


def main() -> None:
    bucket = os.getenv("DECISIONOS_S3_BUCKET", "decisionos-evidence")
    prefix = (os.getenv("DECISIONOS_S3_PREFIX", "evidence/") or "").lstrip("/")
    dest = Path(os.getenv("DECISIONOS_DR_DEST", "var/evidence/restore"))
    policy_path = Path(os.getenv("DECISIONOS_DR_POLICY_PATH", "configs/dr/sample_policy.json"))
    dry_run = os.getenv("DECISIONOS_DR_DRY_RUN", "0") == "1"

    policy = _load_policy(policy_path)
    include = policy.get("include_globs") or ["*.json"]
    exclude = policy.get("exclude_globs") or []
    max_files = int(policy.get("max_files", 1000))
    verify_lock = bool(policy.get("verify_lock", True))
    verify_sha = bool(policy.get("verify_sha", True))
    flatten = bool(policy.get("flatten", True))

    adapter = select_adapter()
    keys = adapter.list_keys(bucket, prefix)
    keys = sorted(keys)
    selected: List[str] = []
    for key in keys:
        name = key.split("/")[-1]
        if include and not any(fnmatch(name, pat) for pat in include):
            continue
        if exclude and any(fnmatch(name, pat) for pat in exclude):
            continue
        selected.append(key)
        if len(selected) >= max_files:
            break

    index_map = _index_hash_map(Path(os.getenv("DECISIONOS_EVIDENCE_INDEX", "var/evidence/index.json")))

    restored: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    for key in selected:
        try:
            obj = adapter.get_object(bucket, key)
            body: bytes = obj["Body"]
            name = key.split("/")[-1]
            dst = dest / name if flatten else dest / key
            if dry_run:
                restored.append({"key": key, "dest": str(dst), "dry_run": True})
                continue

            _ensure_parent(dst)
            dst.write_bytes(body)
            sha = _sha256_bytes(body)

            lock_ok = True
            if verify_lock:
                lock_ok = obj.get("Lock") is not None
            sha_ok = True
            if verify_sha and index_map.get(name):
                sha_ok = sha == index_map[name]

            restored.append(
                {
                    "key": key,
                    "dest": str(dst),
                    "sha": sha,
                    "lock_ok": lock_ok,
                    "sha_ok": sha_ok,
                }
            )
        except Exception as exc:  # pragma: no cover - defensive
            failed.append({"key": key, "error": str(exc)})

    report = {
        "mode": os.getenv("DECISIONOS_S3_MODE", "stub"),
        "bucket": bucket,
        "prefix": prefix,
        "dest": str(dest),
        "policy": {
            "include": include,
            "exclude": exclude,
            "max_files": max_files,
            "verify_lock": verify_lock,
            "verify_sha": verify_sha,
            "flatten": flatten,
            "dry_run": dry_run,
        },
        "counts": {"selected": len(selected), "restored": len(restored), "failed": len(failed)},
        "restored": restored,
        "failed": failed,
    }
    report_path = Path(os.getenv("DECISIONOS_DR_REPORT_PATH", "var/dr/restore-report.json"))
    _ensure_parent(report_path)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"[dr-restore] mode={report['mode']} selected={len(selected)} "
        f"restored={len(restored)} failed={len(failed)} -> {report_path}"
    )


if __name__ == "__main__":
    main()
