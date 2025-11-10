from __future__ import annotations

import argparse
import json
import os
import re
from typing import Any, Dict, List, Tuple

import httpx

from apps.i18n.messages import reason_message
from apps.judge.slo_judge import evaluate


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _extract_pr_number_from_ref(ref: str | None) -> int | None:
    match = re.match(r"refs/pull/(\d+)/", ref or "")
    return int(match.group(1)) if match else None


def _load_artifacts_json(path: str | None) -> List[Dict[str, str]]:
    if path and os.path.exists(path):
        raw = _load_json(path)
        artifacts = raw.get("artifacts") or []
        return [a for a in artifacts if a.get("url")]
    repo = os.getenv("GITHUB_REPOSITORY")
    base = os.getenv("GITHUB_SERVER_URL", "https://github.com")
    run_id = os.getenv("GITHUB_RUN_ID")
    if repo and run_id:
        return [{"name": "Artifacts", "url": f"{base}/{repo}/actions/runs/{run_id}#artifacts"}]
    return []


def _normalize_reasons(raw_reasons: List[Any], locale: str) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    normalized: List[Dict[str, str]] = []
    details: List[Dict[str, str]] = []
    seen: set[str] = set()

    for entry in raw_reasons or []:
        if isinstance(entry, dict):
            code = entry.get("code") or entry.get("message") or "unknown"
            message = entry.get("message") or reason_message(code, locale)
            if code not in seen:
                normalized.append({"code": code, "message": message})
                seen.add(code)
            continue
        text = str(entry)
        if ":" in text:
            code, detail = text.split(":", 1)
        else:
            code, detail = text, ""
        code = code.strip()
        detail = detail.strip()
        message = reason_message(code, locale)
        if code not in seen:
            normalized.append({"code": code, "message": message})
            seen.add(code)
        if detail:
            details.append({"code": code, "detail": detail})
    return normalized, details


def _summarize(
    decision: str,
    info: Dict[str, Any],
    trend: Dict[str, Any] | None,
    locale: str,
    artifacts: List[Dict[str, str]],
) -> str:
    icon = "✅ PASS" if decision == "pass" else "❌ FAIL"
    lines = [f"## Release Gate: {icon}"]

    reasons = info.get("reasons") or []
    if reasons:
        lines.append("### 현재 주 사유")
        for reason in reasons[:5]:
            lines.append(f"- `{reason['code']}` — {reason.get('message')}")
    else:
        lines.append("_사유 없음(모든 기준 충족)_")

    if trend:
        lines.append(f"\n### 최근 추세(Top-10, {trend.get('window_days', 7)}일)")
        for code, count in (trend.get("total_top") or [])[:10]:
            lines.append(f"- `{code}` x {count}")

    evidence_path = "var/evidence/latest.json"
    if os.path.exists(evidence_path):
        lines.append(f"\n📎 Evidence: `{evidence_path}`")
    report_path = "var/reports/reason_trend.md"
    if os.path.exists(report_path):
        lines.append(f"📊 Trend Report: `{report_path}`")

    if artifacts:
        lines.append("\n### Artifacts")
        for artifact in artifacts:
            lines.append(f"- [{artifact.get('name', 'artifact')}]({artifact.get('url')})")

    return "\n".join(lines)


def _post_pr_comment(repo: str, pr: int, body: str, token: str) -> None:
    url = f"https://api.github.com/repos/{repo}/issues/{pr}/comments"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    with httpx.Client(timeout=30) as client:
        client.post(url, json={"body": body}, headers=headers)


def main() -> None:
    parser = argparse.ArgumentParser(description="Annotate release gate result on PRs.")
    parser.add_argument("--slo", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--trend")
    parser.add_argument("--artifacts")
    parser.add_argument("--pr", type=int)
    parser.add_argument("--locale", default=os.getenv("DECISIONOS_LOCALE", "ko-KR"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        slo = _load_json(args.slo)
        evidence = _load_json(args.evidence)
        decision, raw_reasons = evaluate(evidence, slo)
    except Exception as exc:
        decision = "fail"
        raw_reasons = [f"infra.error:{exc}"]

    reasons, details = _normalize_reasons(raw_reasons, args.locale)
    info = {"reasons": reasons, "meta": {"reason_detail": details}}
    trend = _load_json(args.trend) if args.trend and os.path.exists(args.trend) else None
    artifacts = _load_artifacts_json(args.artifacts)

    body = _summarize(decision, info, trend, args.locale, artifacts)
    print(body)

    if os.getenv("GITHUB_EVENT_NAME") != "pull_request":
        return

    pr_number = args.pr or _extract_pr_number_from_ref(os.getenv("GITHUB_REF"))
    repo = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")

    if args.dry_run or not (pr_number and repo and token):
        return

    try:
        _post_pr_comment(repo, pr_number, body, token)
    except Exception as exc:
        print(f"[warn] PR comment failed: {exc}")


if __name__ == "__main__":
    main()
