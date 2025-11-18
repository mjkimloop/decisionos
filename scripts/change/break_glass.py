from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from apps.judge.crypto import MultiKeyLoader, hmac_sign_canonical

def _loader() -> MultiKeyLoader:
    loader = MultiKeyLoader(env_var="DECISIONOS_POLICY_KEYS", file_env="DECISIONOS_POLICY_KEYS_FILE")
    loader.force_reload()
    return loader


def _now() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _manifest_path() -> Path:
    return Path(os.environ.get("DECISIONOS_BREAK_GLASS_MANIFEST", "var/change/breakglass.json"))


def _write_manifest(data: Dict[str, Any]) -> None:
    path = _manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def issue_token(reason: str, approved_by: str, ttl: int, token: str | None = None) -> Dict[str, Any]:
    manifest = {
        "token": token or uuid.uuid4().hex,
        "reason": reason,
        "approved_by": approved_by,
        "issued_at": _now(),
        "expires_at": _now() + ttl,
    }
    loader = _loader()
    key = loader.choose_active()
    if not key:
        raise RuntimeError("no active policy key available for break-glass manifest")
    signature = {"key_id": key.key_id, "hmac_sha256": hmac_sign_canonical(manifest, key.secret)}
    payload = {"manifest": manifest, "signature": signature}
    _write_manifest(payload)
    return payload


def load_manifest() -> Dict[str, Any]:
    path = _manifest_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def verify_token(token: str | None = None) -> bool:
    payload = load_manifest()
    manifest = payload.get("manifest")
    signature = payload.get("signature")
    if not manifest or not signature:
        return False
    if token and token != manifest.get("token"):
        return False
    if int(manifest.get("expires_at", 0)) < _now():
        return False
    loader = _loader()
    material = loader.get(signature.get("key_id", ""))
    if not material:
        return False
    computed = hmac_sign_canonical(manifest, material.secret)
    return computed == signature.get("hmac_sha256")


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Break-glass token manager")
    sub = parser.add_subparsers(dest="command", required=True)

    issue = sub.add_parser("issue", help="Issue a break-glass token")
    issue.add_argument("--reason", required=True)
    issue.add_argument("--approved-by", required=True)
    issue.add_argument("--ttl", type=int, default=int(os.getenv("DECISIONOS_BREAK_GLASS_TTL_SEC", "1800")))
    issue.add_argument("--token", default=None)

    verify = sub.add_parser("verify", help="Verify token validity")
    verify.add_argument("--token", default=None)

    sub.add_parser("status", help="Show manifest summary")
    sub.add_parser("revoke", help="Delete manifest")

    args = parser.parse_args(argv)

    if args.command == "issue":
        payload = issue_token(args.reason, args.approved_by, args.ttl, args.token)
        print(json.dumps(payload, indent=2))
        print(f"TOKEN={payload['manifest']['token']}")
        return 0

    if args.command == "verify":
        if verify_token(args.token):
            print("break-glass token valid")
            return 0
        print("break-glass token invalid", file=sys.stderr)
        return 2

    if args.command == "status":
        payload = load_manifest()
        print(json.dumps(payload or {"status": "none"}, indent=2))
        return 0

    if args.command == "revoke":
        path = _manifest_path()
        if path.exists():
            path.unlink()
            print("break-glass manifest removed")
        else:
            print("no manifest found")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(cli())
