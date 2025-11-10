from __future__ import annotations
import argparse, json, os, sys


def summarize(evidence_path: str) -> str:
    try:
        with open(evidence_path, "r", encoding="utf-8") as f:
            ev = json.load(f)
    except Exception:
        return ":warning: evidence not found"

    parts = []
    perf = ev.get("perf") or {}
    if perf:
        lat = perf.get("latency_ms", {})
        err = perf.get("error_rate")
        parts.append(f"latency p95={lat.get('p95')} p99={lat.get('p99')} error_rate={err}")
    budget = (ev.get("budget") or {}).get("level")
    if budget:
        parts.append(f"budget={budget}")
    quota = (ev.get("quota") or {}).get("decisions") or {}
    if quota:
        denied = [k for k, v in quota.items() if v.get("action") == "deny"]
        if denied:
            parts.append(f"quota deny: {','.join(denied)}")
    return " | ".join(parts) or "no summary"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--infra-fail", default="")
    ap.add_argument("--canary-fail", default="")
    args = ap.parse_args()

    summary = summarize(args.evidence)
    failed = []
    if args.infra_fail == "1":
        failed.append("infra")
    if args.canary_fail == "1":
        failed.append("canary")

    body = f"**Release Gates**: {'FAIL' if failed else 'PASS'}\n\n"
    if failed:
        body += f"- Failed: {', '.join(failed)}\n"
    body += f"- Evidence Summary: {summary}\n"
    print(body)


if __name__ == "__main__":
    main()
