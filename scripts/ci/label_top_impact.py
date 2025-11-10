from __future__ import annotations

import argparse
import json
import os
import re
from typing import Any, Dict, List

import httpx

LABEL_PREFIX = "reason: "
LABEL_COLOR = "BFD4F2"


def _load_trend(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _extract_pr_number_from_ref(ref: str | None) -> int | None:
    match = re.match(r"refs/pull/(\d+)/", ref or "")
    return int(match.group(1)) if match else None


def _select_labels(trend: Dict[str, Any], topK: int) -> List[str]:
    return [f"{LABEL_PREFIX}{code}" for code, _ in (trend.get("total_top") or [])[:topK]]


def _ensure_labels(repo: str, labels: List[str], token: str) -> None:
    api = f"https://api.github.com/repos/{repo}/labels"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    with httpx.Client(timeout=30) as client:
        existing = set()
        resp = client.get(api, headers=headers)
        resp.raise_for_status()
        for item in resp.json():
            existing.add(item["name"])
        for name in labels:
            if name not in existing:
                client.post(api, headers=headers, json={"name": name, "color": LABEL_COLOR})


def _list_current_reason_labels(repo: str, pr: int, token: str) -> List[str]:
    api = f"https://api.github.com/repos/{repo}/issues/{pr}/labels"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    with httpx.Client(timeout=30) as client:
        resp = client.get(api, headers=headers)
        resp.raise_for_status()
        return [item["name"] for item in resp.json() if item["name"].startswith(LABEL_PREFIX)]


def _set_labels(repo: str, pr: int, labels: List[str], token: str) -> None:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    issue_labels_api = f"https://api.github.com/repos/{repo}/issues/{pr}/labels"
    with httpx.Client(timeout=30) as client:
        for label in _list_current_reason_labels(repo, pr, token):
            client.delete(f"{issue_labels_api}/{label}", headers=headers)
        if labels:
            client.post(issue_labels_api, headers=headers, json={"labels": labels})


def main() -> None:
    parser = argparse.ArgumentParser(description="Label PRs with top-impact reason codes.")
    parser.add_argument("--trend", required=True)
    parser.add_argument("--topK", type=int, default=3)
    parser.add_argument("--pr", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")
    if not repo or not token:
        print("[label] missing repo/token; skip")
        return

    pr_number = args.pr or _extract_pr_number_from_ref(os.getenv("GITHUB_REF"))
    if not pr_number:
        print("[label] no PR detected; skip")
        return

    trend = _load_trend(args.trend)
    desired = _select_labels(trend, args.topK)
    print(f"[label] desired labels: {desired}")
    if args.dry_run or not desired:
        return

    _ensure_labels(repo, desired, token)
    _set_labels(repo, pr_number, desired, token)


if __name__ == "__main__":
    main()
