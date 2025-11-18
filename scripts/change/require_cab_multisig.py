from __future__ import annotations

import argparse
from typing import Dict, List, Optional, Set

from apps.common.policy_loader import load_approval_policy, load_ownership_policy
from scripts.change.utils import append_reason, parse_csv, update_status


def _service_entry(service: str, ownership: Dict[str, dict]) -> Dict[str, List[str]]:
    for item in ownership.get("services", []):
        if item.get("name") == service:
            return item
    return {}


def _match_rule(service: str, rules: List[dict]) -> dict:
    for rule in rules:
        match = rule.get("match", {})
        services = match.get("services")
        if services and "*" not in services and service not in services:
            continue
        return rule
    return {}


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Require CAB multisig")
    parser.add_argument("--service", required=True)
    parser.add_argument("--signers", default="")
    parser.add_argument("--status-file", default="var/ci/change_status.json")
    parser.add_argument("--reasons-json", default="var/gate/reasons.json")
    args = parser.parse_args(argv)

    signers = set(parse_csv(args.signers))
    approval = load_approval_policy()
    ownership = load_ownership_policy()
    rule = _match_rule(args.service, approval.get("rules", []))
    min_signatures = int(rule.get("min_signatures", 1))
    result = {"service": args.service, "signers": sorted(signers), "rule": rule.get("name", "default")}

    if len(signers) < min_signatures:
        append_reason(args.reasons_json, "reason:cab-missing", f"{len(signers)}/{min_signatures}")
        update_status(args.status_file, "cab", "blocked", result)
        print(f"[change] CAB signers insufficient ({len(signers)}/{min_signatures})")
        return 2

    required_signers = set(rule.get("required_signers") or [])
    missing_required = required_signers - signers
    if missing_required:
        append_reason(args.reasons_json, "reason:cab-required", ",".join(sorted(missing_required)))
        update_status(args.status_file, "cab", "blocked", result)
        print(f"[change] CAB missing required signers: {', '.join(sorted(missing_required))}")
        return 2

    min_roles = rule.get("min_roles") or {}
    if "cab" in min_roles:
        entry = _service_entry(args.service, ownership)
        cab_pool = set(entry.get("cab") or [])
        cab_signed = len(signers & cab_pool)
        required = int(min_roles["cab"])
        if cab_signed < required:
            append_reason(args.reasons_json, "reason:cab-role-missing", f"{cab_signed}/{required}")
            update_status(args.status_file, "cab", "blocked", result)
            print(f"[change] CAB role requirement unmet ({cab_signed}/{required})")
            return 2

    update_status(args.status_file, "cab", "ok", result)
    print("[change] CAB multisig satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
