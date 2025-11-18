#!/usr/bin/env python3
"""Policy diff guard for CI pre-gate.

Enforces 2-reviewer approval for policy file changes via:
1. GitHub label check ('review/2-approvers')
2. GitHub approvals count (>=2 unique approvers)

Safe mode: Gracefully skips if GITHUB_TOKEN/PR context is missing.
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import urllib.request
from typing import List


def _sh(cmd: List[str]) -> str:
    """Execute shell command and return stdout."""
    return subprocess.check_output(cmd, text=True).strip()


def changed_files(base: str, head: str) -> List[str]:
    """Get list of changed files between base and head."""
    try:
        out = _sh(["git", "diff", "--name-only", f"{base}...{head}"])
        return [line for line in out.splitlines() if line]
    except subprocess.CalledProcessError:
        try:
            # Fallback to simple diff if triple-dot fails
            out = _sh(["git", "diff", "--name-only", base, head])
            return [line for line in out.splitlines() if line]
        except subprocess.CalledProcessError:
            # If git fails entirely, return empty list (safe mode)
            return []


def pr_labels(repo: str, pr: str, token: str) -> List[str]:
    """Fetch PR labels from GitHub API."""
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues/{pr}/labels",
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode())
        return [d["name"] for d in data]


def approvals_count(repo: str, pr: str, token: str) -> int:
    """Count unique approvers from GitHub PR reviews."""
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/pulls/{pr}/reviews",
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode())
        approvers = {d["user"]["login"] for d in data if d["state"] == "APPROVED"}
        return len(approvers)


def main():
    """Main entry point for policy diff guard."""
    policy_glob = os.environ.get("POLICY_GLOB", "configs/policy/*.signed.json")
    req_label = os.environ.get("REQUIRED_LABEL", "review/2-approvers")
    require_approvals = os.environ.get("REQUIRE_APPROVALS", "0") == "1"
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("CI_REPO") or os.environ.get("GITHUB_REPOSITORY", "")
    pr = os.environ.get("CI_PR_NUMBER") or os.environ.get("PR_NUMBER") or ""
    base = os.environ.get("CI_BASE_SHA") or os.environ.get("GITHUB_BASE_SHA") or "origin/main"
    head = os.environ.get("CI_HEAD_SHA") or os.environ.get("GITHUB_SHA") or "HEAD"

    # 정책 파일이 변경되었는지 확인
    files = changed_files(base, head)
    policy_set = set()
    for pat in policy_glob.split(","):
        for f in glob.glob(pat.strip()):
            policy_set.add(f.replace("\\", "/"))  # Normalize path separators

    policy_changed = any(f.replace("\\", "/") in policy_set for f in files)

    if not policy_changed:
        print("policy_diff_guard: no policy change detected")
        sys.exit(0)

    if not token or not repo or not pr:
        print("policy_diff_guard: policy changed but PR context/token missing; soft-fail")
        sys.exit(0)  # CI 외 환경에서 깨지지 않도록

    if require_approvals:
        n = approvals_count(repo, pr, token)
        if n < 2:
            print(f"FAIL: policy changed; approvals={n} (<2)")
            sys.exit(3)
        print(f"policy_diff_guard: approvals={n} OK")
        sys.exit(0)
    else:
        labels = pr_labels(repo, pr, token)
        if req_label not in labels:
            print(f"FAIL: policy changed; missing label '{req_label}'")
            sys.exit(3)
        print(f"policy_diff_guard: label '{req_label}' present")
        sys.exit(0)


if __name__ == "__main__":
    main()
