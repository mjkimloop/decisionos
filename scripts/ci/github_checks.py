from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_VERSION = "2022-11-28"


def build_payload(name: str, sha: str, conclusion: str, summary: str, title: str, text: str, details_url: str):
    payload = {
        "name": name,
        "head_sha": sha,
        "status": "completed",
        "conclusion": conclusion,
        "output": {
            "title": title or name,
            "summary": summary or "Release gate status",
        },
    }
    if text:
        payload["output"]["text"] = text
    if details_url:
        payload["details_url"] = details_url
    return payload


def send_check(repo: str, token: str, payload: dict) -> str:
    url = f"https://api.github.com/repos/{repo}/check-runs"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
        },
    )
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update GitHub Checks for release gate")
    parser.add_argument("--status", choices=["pass", "fail", "warn"], default="pass")
    parser.add_argument("--summary", default="Release gate completed")
    parser.add_argument("--text", default="")
    parser.add_argument("--details-url", default=os.getenv("GITHUB_SERVER_URL", ""))
    parser.add_argument("--repo", default=os.getenv("CI_REPO") or os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--sha", default=os.getenv("GITHUB_SHA", ""))
    parser.add_argument("--name", default="Release Gate")
    parser.add_argument("--title", default="")
    parser.add_argument("--reasons-json", default="")
    return parser.parse_args()


def _load_reasons(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return ""
    reasons = []
    if isinstance(data, dict):
        reasons = data.get("reasons") or []
    elif isinstance(data, list):
        reasons = data
    codes = [entry.get("code") for entry in reasons if isinstance(entry, dict) and entry.get("code")]
    if not codes:
        return ""
    return " Top reasons: " + ", ".join(codes[:5])


def main() -> int:
    args = parse_args()
    if os.getenv("DECISIONOS_VISIBILITY_ENABLE", "1") == "0":
        print("[checks] visibility disabled; skipping")
        return 0
    token = os.getenv("GITHUB_TOKEN")
    if not token or not args.repo or not args.sha:
        print("[checks] missing token/repo/sha; skipping")
        return 0
    conclusion_map = {"pass": "success", "fail": "failure", "warn": "neutral"}
    summary = args.summary + (_load_reasons(args.reasons_json) if args.reasons_json else "")
    payload = build_payload(args.name, args.sha, conclusion_map[args.status], summary, args.title or args.name, args.text, args.details_url)
    try:
        response = send_check(args.repo, token, payload)
        print("[checks] updated:", response)
    except urllib.error.HTTPError as exc:
        print(f"[checks] GitHub API error: {exc.read().decode()}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover
        print(f"[checks] failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
