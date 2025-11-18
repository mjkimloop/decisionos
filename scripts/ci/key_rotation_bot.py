#!/usr/bin/env python3
"""Key rotation bot: Auto-create PR/Issue when keys expire soon.

Creates draft PR with:
- Branch: chore/rotate-keys-YYYYMMDD
- Commit: Rotation notice document
- Labels: rotation:soon-{14,7,3} based on days left
- Fallback to Issue if PR creation fails
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import urllib.request
from typing import Any, Dict, List, Optional

ISO = "%Y-%m-%dT%H:%M:%SZ"


def days_left(not_after: Optional[str]) -> float:
    """Calculate days remaining until key expires."""
    if not not_after:
        return 9999.0
    expiry = dt.datetime.strptime(not_after, ISO)
    return (expiry - dt.datetime.utcnow()).total_seconds() / 86400.0


def parse_keys() -> List[Dict[str, Any]]:
    """Parse keys from environment."""
    raw = os.environ.get("DECISIONOS_POLICY_KEYS") or os.environ.get("DECISIONOS_JUDGE_KEYS") or "[]"
    return json.loads(raw)


def ensure_labels() -> int:
    """Ensure countdown labels exist."""
    return subprocess.call([sys.executable, "-m", "scripts.ci.ensure_rotation_labels"])


def gh_api(path: str, token: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
    """Call GitHub API."""
    req = urllib.request.Request(f"https://api.github.com{path}", method=method)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github+json")

    payload = None
    if data is not None:
        payload = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, payload) as r:
        return json.loads(r.read().decode() or "{}")


def open_issue(repo: str, token: str, title: str, body: str, labels: List[str]) -> Dict[str, Any]:
    """Create GitHub issue."""
    data = {"title": title, "body": body, "labels": labels}
    return gh_api(f"/repos/{repo}/issues", token, "POST", data)


def create_pr(
    repo: str,
    token: str,
    base: str,
    head: str,
    title: str,
    body: str,
    draft: bool = True,
    labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create GitHub PR."""
    data = {"base": base, "head": head, "title": title, "body": body, "draft": draft}
    pr = gh_api(f"/repos/{repo}/pulls", token, "POST", data)

    if labels:
        gh_api(f"/repos/{repo}/issues/{pr['number']}/labels", token, "POST", {"labels": labels})

    return pr


def main() -> int:
    """Main entry point."""
    if os.environ.get("ROTATION_PR_ENABLE", "1") != "1":
        print("rotation bot disabled")
        return 0

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("CI_REPO") or os.environ.get("GITHUB_REPOSITORY")

    if not token or not repo:
        print("no token/repo; skip")
        return 0

    keys = parse_keys()
    soon_days = int(os.environ.get("ROTATION_SOON_DAYS", "14"))

    # Find keys expiring soon
    warn = [k for k in keys if k.get("state") in ("active", "grace") and days_left(k.get("not_after")) <= soon_days]

    if not warn:
        print("no soon-to-expire keys")
        return 0

    # Ensure countdown labels exist
    ensure_labels()

    # Determine which labels to apply
    labels = set()
    for k in warn:
        d = days_left(k.get("not_after"))
        if d <= 3:
            labels.add("rotation:soon-3")
        elif d <= 7:
            labels.add("rotation:soon-7")
        else:
            labels.add("rotation:soon-14")

    # Get base branch
    base = os.environ.get("ROTATION_PR_BASE", "")
    if not base:
        repo_info = gh_api(f"/repos/{repo}", token)
        base = repo_info.get("default_branch", "main")

    # Create branch name
    head = f"{os.environ.get('ROTATION_BRANCH_PREFIX', 'chore/rotate-keys')}-{dt.datetime.utcnow().strftime('%Y%m%d')}"

    # Git operations
    try:
        subprocess.check_call(["git", "config", "user.email", "bot@decisionos.local"])
        subprocess.check_call(["git", "config", "user.name", "decisionos-bot"])
        subprocess.check_call(["git", "fetch", "origin", base])
        subprocess.check_call(["git", "checkout", "-B", head, f"origin/{base}"])

        # Create rotation notice document
        path = f"docs/ops/ROTATION-NOTICE-{dt.datetime.utcnow().strftime('%Y%m%d')}.md"
        os.makedirs(os.path.dirname(path), exist_ok=True)

        body_lines = [
            "# Key Rotation Notice\n",
            "\n",
            "|key_id|state|not_after|days_left|\n",
            "|---|---|---|---|\n",
        ]

        for k in sorted(warn, key=lambda x: days_left(x.get("not_after"))):
            key_id = k.get("key_id", "unknown")
            state = k.get("state", "unknown")
            not_after = k.get("not_after", "N/A")
            days = days_left(k.get("not_after"))
            body_lines.append(f"|{key_id}|{state}|{not_after}|{days:.1f}|\n")

        with open(path, "w", encoding="utf-8") as f:
            f.writelines(body_lines)

        subprocess.check_call(["git", "add", path])
        subprocess.check_call(["git", "commit", "-m", "chore: rotation notice"])
        subprocess.check_call(["git", "push", "-f", "origin", head])

    except subprocess.CalledProcessError as e:
        print(f"git operations failed: {e}", file=sys.stderr)
        return 1

    # Create PR
    title = f"[Rotation] Keys expiring within {soon_days}d"
    pr_body = "".join(body_lines) + "\n\n> 자동 생성: key_rotation_bot\n"

    try:
        pr = create_pr(repo, token, base, head, title, pr_body, draft=True, labels=list(labels))
        print(f"PR #{pr['number']} created")
    except Exception as e:
        if os.environ.get("ALLOW_ISSUE_FALLBACK", "1") == "1":
            issue = open_issue(repo, token, title, pr_body, list(labels))
            print(f"Issue #{issue['number']} created (fallback)")
        else:
            raise

    return 0


if __name__ == "__main__":
    sys.exit(main())
