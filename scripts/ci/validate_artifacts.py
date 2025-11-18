from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path
from typing import Dict, Tuple

from apps.judge.crypto import MultiKeyLoader, hmac_sign_canonical


def _read_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"{path} missing")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} invalid json: {exc}") from exc


def _validate_index(path: Path) -> Dict[str, object]:
    data = _read_json(path)
    items = data.get("items")
    if not isinstance(items, list) or not items:
        items = data.get("files")
        if not isinstance(items, list) or not items:
            raise ValueError("missing items/files list")
    sample = items[0]
    for field in ("path", "sha256"):
        if field not in sample:
            raise ValueError(f"item missing {field}")
    return {"path": str(path), "count": len(items), "generated_at": data.get("generated_at"), "data": data}


def _validate_gc(path: Path) -> Dict[str, object]:
    data = _read_json(path)
    totals = data.get("totals")
    if not isinstance(totals, dict):
        raise ValueError("missing totals")
    if "scanned" not in totals:
        raise ValueError("totals.scanned missing")
    policy = data.get("policy") or {}
    return {"path": str(path), "scanned": totals.get("scanned"), "policy": policy, "data": data}


def _validate_upload(path: Path) -> Dict[str, object]:
    data = _read_json(path)
    counts = data.get("counts")
    if not isinstance(counts, dict):
        raise ValueError("missing counts")
    required = {"uploaded", "skipped", "failed"}
    if not required.issubset(counts.keys()):
        raise ValueError("counts missing fields")
    return {"path": str(path), "mode": data.get("mode", "unknown"), "counts": counts, "data": data}


def _validate_dr(path: Path) -> Dict[str, object]:
    data = _read_json(path)
    counts = data.get("counts")
    if not isinstance(counts, dict):
        raise ValueError("missing counts")
    if "restored" not in counts:
        raise ValueError("counts.restored missing")
    return {"path": str(path), "restored": counts.get("restored"), "failed": counts.get("failed", 0), "data": data}


VALIDATORS = {
    "index": _validate_index,
    "gc": _validate_gc,
    "upload": _validate_upload,
    "dr": _validate_dr,
}


def assert_object_lock(upload_report: dict) -> None:
    obj_lock = upload_report.get("object_lock") or {}
    enabled = obj_lock.get("applied") is True and obj_lock.get("mode", "").upper() == "COMPLIANCE"
    if not enabled:
        raise SystemExit("FAIL: Evidence upload missing ObjectLock COMPLIANCE enforcement")


def assert_pii_on_when_prod(env: Dict[str, str]) -> None:
    if env.get("DECISIONOS_MODE") == "prod" and env.get("DECISIONOS_PII_ENABLE") != "1":
        raise SystemExit("FAIL: PII must be enabled in prod (DECISIONOS_PII_ENABLE=1)")


def _load_policy_loader() -> MultiKeyLoader:
    loader = MultiKeyLoader(env_var="DECISIONOS_POLICY_KEYS", file_env="DECISIONOS_POLICY_KEYS_FILE")
    loader.force_reload()
    if loader.info().get("key_count"):
        return loader
    fallback = MultiKeyLoader()
    fallback.force_reload()
    return fallback


def verify_signed_policy(pattern: str) -> None:
    loader = _load_policy_loader()
    info = loader.info()
    if not info.get("key_count"):
        print("[validate_artifacts] WARN: no policy keys loaded; skipping signature verification")
        return
    matched = False
    for file in glob.glob(pattern):
        matched = True
        data = _read_json(Path(file))
        payload = data.get("payload")
        signature = data.get("signature") or {}
        if not isinstance(payload, dict) or not signature:
            raise SystemExit(f"FAIL: {file} missing payload/signature")
        key_id = signature.get("key_id")
        material = loader.get(key_id) if key_id else None
        if not material:
            raise SystemExit(f"FAIL: {file} unknown key_id {key_id}")
        expected = hmac_sign_canonical(payload, material.secret)
        if expected != signature.get("hmac_sha256"):
            raise SystemExit(f"FAIL: {file} signature mismatch")
    if not matched:
        raise SystemExit(f"FAIL: no policy files matched pattern {pattern}")


def validate_artifacts(paths: Dict[str, str]) -> Tuple[bool, Dict[str, Dict[str, object]]]:
    results: Dict[str, Dict[str, object]] = {}
    ok = True
    for key, validator in VALIDATORS.items():
        path = paths.get(key)
        if not path:
            continue
        try:
            results[key] = validator(Path(path))
            results[key]["status"] = "ok"
        except Exception as exc:
            ok = False
            results[key] = {"status": "error", "reason": str(exc), "path": path}
    return ok, results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate release gate artifacts")
    parser.add_argument("--index", help="Path to var/evidence/index.json")
    parser.add_argument("--gc", help="Path to var/evidence/gc-report.json")
    parser.add_argument("--upload", help="Path to var/evidence/upload-report.json")
    parser.add_argument("--dr", help="Path to var/dr/restore-report.json")
    parser.add_argument("--json-out", help="Optional JSON output file")
    parser.add_argument("--objectlock-enforce", action="store_true")
    parser.add_argument("--require-pii-on-when-prod", action="store_true")
    parser.add_argument("--verify-signed-policy", default="")
    return parser.parse_args()


def cli() -> int:
    args = parse_args()
    paths = {k: getattr(args, k) for k in VALIDATORS.keys() if getattr(args, k)}
    ok, details = validate_artifacts(paths)
    if args.objectlock_enforce:
        upload = details.get("upload", {})
        if upload.get("status") != "ok":
            raise SystemExit("FAIL: upload report missing for ObjectLock enforcement")
        assert_object_lock(upload.get("data", {}))
    if args.require_pii_on_when_prod:
        assert_pii_on_when_prod(os.environ)
    if args.verify_signed_policy:
        verify_signed_policy(args.verify_signed_policy)
    out_text = json.dumps({"ok": ok, "details": details}, indent=2)
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(out_text, encoding="utf-8")
    print(out_text)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(cli())
