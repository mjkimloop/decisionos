from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

from apps.judge.crypto import MultiKeyLoader, hmac_sign_canonical


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_plan(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rotate(plan_path: str, out_path: str) -> Dict[str, Any]:
    plan = _load_plan(plan_path)
    loader = MultiKeyLoader()
    loader.force_reload()
    active = loader.choose_active()
    if not active:
        raise SystemExit("no active key to rotate from")

    new_key_id = f"kr-{_now().strftime('%Y%m%d%H%M%S')}"
    new_secret = os.urandom(32)
    manifest = {
        "old_key_id": active.key_id,
        "new_key_id": new_key_id,
        "issued_at": _now().isoformat().replace("+00:00", "Z"),
        "phases": plan.get("phases", []),
    }
    sig = hmac_sign_canonical(manifest, active.secret)
    payload = {"manifest": manifest, "signature": {"key_id": active.key_id, "hmac_sha256": sig}}
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dummy key rotation (plan + manifest output)")
    parser.add_argument("--plan", required=True, help="Path to key_rotation_plan.json")
    parser.add_argument("--out", default="var/keys/rotation_manifest.json")
    args = parser.parse_args(argv)

    payload = rotate(args.plan, args.out)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
