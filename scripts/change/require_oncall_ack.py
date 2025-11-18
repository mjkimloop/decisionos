from __future__ import annotations

import argparse
from typing import List, Set

from apps.common.policy_loader import load_ownership_policy
from scripts.change.utils import append_reason, parse_csv, update_status


def _resolve_oncall(service: str) -> Set[str]:
    ownership = load_ownership_policy()
    for item in ownership.get("services", []):
        if item.get("name") == service:
            return set(item.get("oncall") or [])
    return set()


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Require on-call acknowledgement")
    parser.add_argument("--service", required=True)
    parser.add_argument("--ack-users", default="")
    parser.add_argument("--status-file", default="var/ci/change_status.json")
    parser.add_argument("--reasons-json", default="var/gate/reasons.json")
    args = parser.parse_args(argv)

    ack_users = set(parse_csv(args.ack_users))
    required = _resolve_oncall(args.service)
    info = {"service": args.service, "acks": sorted(ack_users), "required": sorted(required)}
    if not required:
        update_status(args.status_file, "oncall", "ok", info)
        print(f"[change] no on-call mapping for {args.service}, skipping")
        return 0
    if ack_users & required:
        update_status(args.status_file, "oncall", "ok", info)
        print("[change] on-call ack confirmed")
        return 0
    append_reason(args.reasons_json, "reason:oncall-missing", args.service)
    update_status(args.status_file, "oncall", "blocked", info)
    print(f"[change] on-call ack missing for {args.service}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
