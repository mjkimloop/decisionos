from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List
from urllib import request, error

import time

from apps.ops import metrics_burn

SEVERITY_RANK = {"critical": 3, "warn": 2, "ok": 0, "unknown": 0}


def _append_reason(code: str, message: str, *, path: str) -> None:
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    reasons: List[Dict[str, object]] = []
    if file.exists():
        try:
            reasons = json.loads(file.read_text(encoding="utf-8"))
        except Exception:
            reasons = []
    reasons.append({"code": code, "message": message, "count": 1})
    file.write_text(json.dumps(reasons, ensure_ascii=False, indent=2), encoding="utf-8")


def _freeze_flag(reason: str) -> None:
    flag_path = Path(os.getenv("DECISIONOS_FREEZE_FILE", "var/release/freeze.flag"))
    flag_path.parent.mkdir(parents=True, exist_ok=True)
    flag_path.write_text(f"freeze={reason} ts={int(time.time())}\n", encoding="utf-8")


def _notify_slack(text: str) -> None:
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook:
        print("[burn_gate] slack webhook not set; skipping notification")
        return
    payload = json.dumps({"text": text}).encode("utf-8")
    req = request.Request(webhook, data=payload, headers={"Content-Type": "application/json"})
    try:
        request.urlopen(req, timeout=5).read()
        print("[burn_gate] slack notification sent")
    except error.URLError as exc:  # pragma: no cover
        print(f"[burn_gate] slack notification failed: {exc}", file=sys.stderr)


def _severity(report: dict) -> str:
    return report.get("overall", {}).get("state", "unknown")


def _filter_windows(report: dict, allowed: List[str]) -> dict:
    if not allowed:
        return report
    keep = set(allowed)
    windows = [w for w in report.get("windows", []) if w.get("name") in keep]
    report = dict(report)
    report["windows"] = windows
    worst = "ok"
    worst_name = ""
    for w in windows:
        state = w.get("state", "ok")
        if SEVERITY_RANK.get(state, 0) > SEVERITY_RANK.get(worst, 0):
            worst = state
            worst_name = w.get("name", "")
    report["overall"] = {"state": worst, "window": worst_name}
    return report


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Burn rate alert + gate")
    parser.add_argument("--policy", default="configs/slo/burn_policy.yaml")
    parser.add_argument("--samples", default=None)
    parser.add_argument("--report", default="var/ci/burn_report.json")
    parser.add_argument("--reasons-json", default="var/gate/reasons.json")
    parser.add_argument("--windows", default=os.getenv("BURN_WINDOWS", ""))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    report = metrics_burn.compute_burn_report(policy_path=args.policy, sample_path=args.samples)
    if args.windows:
        report = _filter_windows(report, [w.strip() for w in args.windows.split(",") if w.strip()])
    metrics_burn.save_report(report, args.report)

    severity = _severity(report)
    print(f"[burn_gate] overall={severity} report={args.report}")

    if args.dry_run or severity in {"ok", "unknown"}:
        return 0

    window = report.get("overall", {}).get("window", "")
    message = f"Burn rate {severity} on window {window or 'n/a'}"
    _append_reason("reason:budget-burn", message, path=args.reasons_json)
    _freeze_flag(reason="burn_gate")
    _notify_slack(f":fire: {message}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
