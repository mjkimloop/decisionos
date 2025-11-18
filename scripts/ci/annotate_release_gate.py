from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Sequence, Tuple
import urllib.request
import urllib.error

from scripts.ci.validate_artifacts import validate_artifacts

MARKER = os.getenv("DECISIONOS_COMMENT_MARKER", "<!-- decisionos:gate -->")
BADGE = {
    "pass": ("🟢", "PASS"),
    "fail": ("🔴", "FAIL"),
    "warn": ("🟡", "WARN"),
    "unknown": ("⚪", "UNKNOWN"),
}


def read_json(path: str) -> dict:
    file = Path(path)
    if not file.exists():
        return {}
    try:
        return json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def parse_artifacts(arg: str) -> Dict[str, str]:
    artifacts: Dict[str, str] = {}
    if not arg:
        return artifacts
    for item in arg.split(","):
        token = item.strip()
        if not token:
            continue
        if "=" in token:
            name, path = token.split("=", 1)
        else:
            name, path = Path(token).stem, token
        artifacts[name.strip()] = path.strip()
    return artifacts


def stage_status_from_env(stage: str) -> str:
    value = os.getenv(stage.upper() + "_RESULT") or os.getenv(stage, "")
    value = value.lower()
    if value in ("success", "passed", "pass"):
        return "pass"
    if value in ("failure", "failed", "fail"):
        return "fail"
    if value in ("cancelled", "skipped", "neutral"):
        return "warn"
    return "unknown"


def collect_stage_statuses(status_json: str) -> Dict[str, str]:
    statuses = {
        "pre_gate": stage_status_from_env("PRE_GATE_RESULT"),
        "gate": stage_status_from_env("GATE_RESULT"),
        "post_gate": stage_status_from_env("POST_GATE_RESULT"),
    }
    extra = read_json(status_json) if status_json else {}
    if isinstance(extra, dict):
        for k in ("pre_gate", "gate", "post_gate"):
            if extra.get(k):
                statuses[k] = extra[k]
    return statuses


def render_badges(statuses: Dict[str, str]) -> str:
    rows = ["| Stage | Status |", "| --- | --- |"]
    for stage in ("pre_gate", "gate", "post_gate"):
        status = statuses.get(stage, "unknown")
        emoji, label = BADGE.get(status, BADGE["unknown"])
        rows.append(f"| {stage.replace('_', ' ').title()} | {emoji} {label} |")
    return "\n".join(rows)


def render_artifacts(validation: Dict[str, Dict[str, object]]) -> str:
    if not validation:
        return "_No artifacts provided._"
    lines = []
    for name, info in validation.items():
        status = info.get("status") == "ok"
        emoji = "✅" if status else "❌"
        summary = ", ".join(f"{k}={v}" for k, v in info.items() if k not in {"status", "path", "data"})
        lines.append(f"- {emoji} **{name}** ({summary})")
    return "\n".join(lines)


def render_reasons(reasons: Sequence[dict]) -> str:
    if not reasons:
        return "_No blocking reasons reported._"
    lines = ["| Code | Message | Count |", "| --- | --- | --- |"]
    for reason in reasons:
        code = reason.get("code", "")
        message = str(reason.get("message", "")).replace("|", "\\|")
        count = reason.get("count", 0)
        lines.append(f"| `{code}` | {message} | {count} |")
    return "\n".join(lines)


def render_top_impact(data: dict, limit: int) -> str:
    entries: List[Tuple[str, float]] = []
    if isinstance(data.get("top"), list):
        for item in data["top"]:
            entries.append((item.get("code") or item.get("module") or "unknown", item.get("score", 0)))
    elif isinstance(data.get("total_top"), list):
        for pair in data["total_top"]:
            if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                entries.append((str(pair[0]), float(pair[1])))
    if not entries:
        return ""
    lines = ["| Rank | Item | Score |", "| --- | --- | ---: |"]
    for idx, (name, score) in enumerate(entries[:limit], 1):
        lines.append(f"| {idx} | `{name}` | {score:.2f} |")
    return "\n".join(lines)


def load_label_weights(path: str, limit: int) -> List[str]:
    catalog = read_json(path)
    labels = catalog.get("labels")
    entries: List[Tuple[str, float]] = []
    if isinstance(labels, dict):
        for name, meta in labels.items():
            entries.append((name, float(meta.get("weight", 0))))
    elif isinstance(labels, list):
        for meta in labels:
            if isinstance(meta, dict) and meta.get("name"):
                entries.append((meta["name"], float(meta.get("weight", 0))))
    entries.sort(key=lambda item: item[1], reverse=True)
    return [name for name, _ in entries[:limit]]


def build_diff_link(requested: str) -> str:
    if requested and requested.lower() != "auto":
        return requested
    repo = os.getenv("GITHUB_REPOSITORY")
    base = os.getenv("GITHUB_BASE_REF")
    head = os.getenv("GITHUB_HEAD_REF") or os.getenv("GITHUB_REF_NAME") or os.getenv("GITHUB_SHA")
    if repo and base and head:
        return f"https://github.com/{repo}/compare/{base}...{head}"
    return "(diff unavailable)"


def gh_request(method: str, path: str, token: str, payload: dict | None = None):
    url = f"https://api.github.com/{path.lstrip('/')}"
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method.upper(),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def upsert_comment(repo: str, pr: str, token: str, body: str):
    path = f"repos/{repo}/issues/{pr}/comments"
    try:
        comments = gh_request("GET", path, token)
    except Exception as exc:
        print(f"[annotate] failed to list comments: {exc}")
        return
    target = None
    for comment in comments:
        if isinstance(comment.get("body"), str) and MARKER in comment["body"]:
            target = comment
            break
    payload = {"body": body}
    if target:
        gh_request("PATCH", f"repos/{repo}/issues/comments/{target['id']}", token, payload)
        print(f"[annotate] updated comment #{target['id']}")
    else:
        gh_request("POST", path, token, payload)
        print("[annotate] created comment")


def sync_labels(repo: str, pr: str, token: str, catalog_path: str, reason_codes: List[str]):
    catalog = read_json(catalog_path)
    labels = catalog.get("labels") or {}
    desired = []
    for code in reason_codes:
        meta = labels.get(code)
        if meta:
            desired.append((code, meta))
    if not desired:
        print("[annotate] no labels to sync")
        return
    for name, meta in desired:
        payload = {"name": name, "color": meta.get("color", "ededed"), "description": meta.get("description", "")}
        try:
            gh_request("PATCH", f"repos/{repo}/labels/{name}", token, payload)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                gh_request("POST", f"repos/{repo}/labels", token, payload)
            else:
                print(f"[annotate] label sync failed for {name}: {exc}")
    gh_request("POST", f"repos/{repo}/issues/{pr}/labels", token, {"labels": [name for name, _ in desired]})
    print(f"[annotate] synced {len(desired)} labels")


def render_change_status(items: Sequence[dict]) -> str:
    if not items:
        return ""
    lines = ["### Change Governance", "| Check | State | Details |", "| --- | --- | --- |"]
    for entry in items:
        info = entry.get("info") or {}
        details = ", ".join(f"{k}={v}" for k, v in info.items()) if info else "—"
        lines.append(f"| {entry.get('name')} | {entry.get('state')} | {details} |")
    return "\n".join(lines)


def build_comment(
    args,
    statuses: Dict[str, str],
    artifacts_text: str,
    reasons_text: str,
    top_impact_text: str,
    diff_link: str,
    top_labels: Sequence[str],
    policy_hash: str,
    dr_summary: str,
    dr_metrics: Dict[str, object],
    tamper_stats: Dict[str, int],
    gameday_md: str,
    change_text: str,
) -> str:
    lines = [
        MARKER,
        "## Release Gate Visibility",
        render_badges(statuses),
        "",
        "### Artifacts",
        artifacts_text,
        "",
        "### Reasons",
        reasons_text,
    ]
    if top_impact_text:
        lines.extend(["", "### Top Impact", top_impact_text])
    label_line = ", ".join(top_labels) if top_labels else "—"
    lines.extend(["", f"**Top-Impact Labels:** {label_line}"])
    if policy_hash:
        lines.append(f"**Policy Hash:** `{policy_hash}`")
    tamper_line = format_tamper_line(tamper_stats)
    if tamper_line:
        lines.append(f"**{tamper_line}**")
    dr_line = format_dr_line(dr_summary, dr_metrics)
    if dr_line:
        lines.append(f"**DR Rehearsal:** {dr_line}")
    if gameday_md:
        lines.extend(["", "### GameDay", gameday_md])
    if change_text:
        lines.extend(["", change_text])
    lines.extend(["", f"**Diff:** {diff_link}", f"_Generated by CI at {os.getenv('GITHUB_RUN_ID', 'local')}_"])
    return "\n".join(lines)


def parse_reasons(path: str) -> Tuple[List[dict], List[str]]:
    data = read_json(path) if path else {}
    reasons = data.get("reasons")
    if reasons is None and isinstance(data, list):
        reasons = data
    if not isinstance(reasons, list):
        return [], []
    codes = [entry.get("code") for entry in reasons if entry.get("code")]
    return reasons, codes


def summarize_dr_report(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""
    data = read_json(path)
    if not data:
        return ""
    status = data.get("status")
    if not status:
        counts = data.get("counts") or {}
        status = "pass" if counts.get("failed", 0) == 0 else "fail"
    link = data.get("report_url") or path
    status_text = status.upper()
    return f"{status_text} ({link})" if link else status_text


def extract_dr_metrics(path: str) -> Dict[str, object]:
    data = read_json(path) if path else {}
    metrics = data.get("metrics") or {}
    counts = data.get("counts") or {}
    return {
        "rto_seconds": metrics.get("rto_seconds") or data.get("rto_seconds"),
        "rpo_files": metrics.get("rpo_files") or counts.get("missed") or counts.get("skipped"),
    }


def extract_tamper_stats(index_path: str) -> Dict[str, int]:
    data = read_json(index_path) if index_path else {}
    summary = data.get("summary") or {}
    return {
        "count": summary.get("count"),
        "tampered": summary.get("tampered"),
        "locked": summary.get("locked"),
    }


def format_dr_line(dr_summary: str, dr_metrics: Dict[str, object]) -> str:
    parts: List[str] = []
    if dr_summary:
        parts.append(dr_summary)
    rto = dr_metrics.get("rto_seconds") if dr_metrics else None
    rpo = dr_metrics.get("rpo_files") if dr_metrics else None
    metrics: List[str] = []
    if rto is not None:
        metrics.append(f"RTO={rto}s")
    if rpo is not None:
        metrics.append(f"RPO={rpo} files")
    if metrics:
        parts.append(", ".join(metrics))
    return " | ".join(parts)


def format_tamper_line(tamper_stats: Dict[str, int]) -> str:
    if not tamper_stats:
        return ""
    if all(v is None for v in tamper_stats.values()):
        return ""
    return "Evidence Integrity: " + ", ".join(
        [
            f"total={tamper_stats.get('count', '?')}",
            f"tampered={tamper_stats.get('tampered', '?')}",
            f"locked={tamper_stats.get('locked', '?')}",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Annotate release gate summary")
    parser.add_argument("--artifacts", default="")
    parser.add_argument("--reasons", default="")
    parser.add_argument("--top-impact", default="")
    parser.add_argument("--status-json", default="")
    parser.add_argument("--diff", default="auto")
    parser.add_argument("--output", default="var/ci/release_gate_comment.md")
    parser.add_argument("--repo", default=os.getenv("CI_REPO") or os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--pr", default=os.getenv("CI_PR_NUMBER") or os.getenv("PR_NUMBER", ""))
    parser.add_argument("--upsert", action="store_true")
    parser.add_argument("--badges", action="store_true")
    parser.add_argument("--sync-labels", action="store_true")
    parser.add_argument("--label-catalog", default="configs/labels/label_catalog_v2.json")
    parser.add_argument("--top-count", type=int, default=int(os.getenv("DECISIONOS_TOP_IMPACT_N", "5")))
    parser.add_argument("--policy-hash", default="")
    parser.add_argument("--dr-report", default="")
    parser.add_argument("--gameday-report", default="")
    parser.add_argument("--change-status", default="var/ci/change_status.json")
    args = parser.parse_args()

    if os.getenv("DECISIONOS_VISIBILITY_ENABLE", "1") == "0":
        print("[annotate] visibility disabled; skipping")
        return 0

    artifact_map = parse_artifacts(args.artifacts)
    valid, details = validate_artifacts(artifact_map)
    artifacts_text = render_artifacts(details)
    statuses = collect_stage_statuses(args.status_json)
    reasons, reason_codes = parse_reasons(args.reasons)
    top_labels = [
        entry.get("code")
        for entry in sorted(reasons, key=lambda r: r.get("count", 0), reverse=True)
        if entry.get("code")
    ][: args.top_count]
    reasons_text = render_reasons(reasons)
    if not top_labels:
        top_labels = load_label_weights(args.label_catalog, args.top_count)
    top_impact_text = render_top_impact(read_json(args.top_impact), args.top_count) if args.top_impact else ""
    diff_link = build_diff_link(args.diff)
    policy_hash = args.policy_hash or os.getenv("POLICY_HASH", "")
    dr_summary = summarize_dr_report(args.dr_report)
    dr_metrics = extract_dr_metrics(args.dr_report)
    tamper_stats = extract_tamper_stats(artifact_map.get("index") or details.get("index", {}).get("path", ""))
    gameday_md = ""
    if args.gameday_report:
        report_file = Path(args.gameday_report)
        if report_file.exists():
            gameday_md = report_file.read_text(encoding="utf-8")
    change_text = ""
    if args.change_status and Path(args.change_status).exists():
        try:
            change_entries = json.loads(Path(args.change_status).read_text(encoding="utf-8"))
            change_text = render_change_status(change_entries if isinstance(change_entries, list) else [])
        except Exception:
            change_text = ""

    if not args.badges:
        statuses = {k: "unknown" for k in statuses}

    comment = build_comment(
        args,
        statuses,
        artifacts_text,
        reasons_text,
        top_impact_text,
        diff_link,
        top_labels,
        policy_hash,
        dr_summary,
        dr_metrics,
        tamper_stats,
        gameday_md,
        change_text,
    )
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(comment, encoding="utf-8")
    print(f"[annotate] wrote {args.output}")

    token = os.getenv("GITHUB_TOKEN")
    if args.upsert and token and args.repo and args.pr:
        try:
            upsert_comment(args.repo, args.pr, token, comment)
        except Exception as exc:
            print(f"[annotate] upsert failed: {exc}")
    elif args.upsert:
        print("[annotate] missing repo/pr/token; skipping comment upsert")

    if args.sync_labels and token and args.repo and args.pr and reason_codes:
        try:
            sync_labels(args.repo, args.pr, token, args.label_catalog, reason_codes)
        except Exception as exc:
            print(f"[annotate] label sync failed: {exc}")
    elif args.sync_labels:
        print("[annotate] label sync skipped (missing token/reasons)")

    if not valid:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
