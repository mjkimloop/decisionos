from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import Iterable, List

from apps.ops import freeze as freeze_guard
from scripts.change.utils import append_reason, parse_csv, update_status


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify change freeze window")
    parser.add_argument("--service", default="core")
    parser.add_argument("--labels", default="")
    parser.add_argument("--status-file", default="var/ci/change_status.json")
    parser.add_argument("--reasons-json", default="var/gate/reasons.json")
    parser.add_argument("--now", default=None, help="Override timestamp (ISO8601)")
    parser.add_argument("--windows", default=None)
    args = parser.parse_args(argv)

    labels = parse_csv(args.labels)
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else None
    blocked, reason = freeze_guard.is_freeze_active(service=args.service, labels=labels, now=now, windows_path=args.windows)
    info = {"service": args.service, "labels": labels, "reason": reason}
    state = "blocked" if blocked else "ok"
    update_status(args.status_file, "freeze", state, info)
    if blocked:
        append_reason(args.reasons_json, "reason:freeze-window", reason or "unknown")
        print(f"[change] freeze window active ({reason})")
        return 2
    print("[change] freeze window check ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
