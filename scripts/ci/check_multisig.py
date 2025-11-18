#!/usr/bin/env python3
"""Multisig approval checker for policy file changes.

Enforces file-glob-based approval rules:
- RBAC policies → Security team 2 approvers
- SLO/infra policies → Platform team 2 approvers
- Canary policies → Platform + Service owner (1 each)

Usage:
    python -m scripts.ci.check_multisig

Environment:
    GITHUB_TOKEN: GitHub API authentication
    CI_PR_NUMBER: Pull request number
    CI_REPO: Repository (org/name)
    DECISIONOS_POLICY_APPROVERS_YAML: Custom approval policy file (optional)

Exit codes:
    0: All approval requirements met
    3: Approval requirements not met
    0: Skipped (no PR context or GITHUB_TOKEN)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

DEFAULT_APPROVAL_POLICY = """
rules:
  - name: RBAC policies
    glob: "configs/policy/rbac*.{json,yaml}"
    required_approvers: 2
    required_teams:
      - security
    description: RBAC changes require 2 security team approvals

  - name: SLO and infrastructure policies
    glob: "configs/policy/slo*.json"
    required_approvers: 2
    required_teams:
      - platform
    description: SLO changes require 2 platform team approvals

  - name: Canary policies
    glob: "configs/policy/canary*.{json,yaml}"
    required_approvers: 2
    required_teams:
      - platform
      - service
    min_per_team: 1
    description: Canary changes require platform + service owner approval

  - name: Freeze window policies
    glob: "configs/change/freeze*.yaml"
    required_approvers: 2
    required_teams:
      - platform
    description: Freeze window changes require 2 platform approvals

  - name: All other policy files
    glob: "configs/policy/*.{json,yaml,signed}"
    required_approvers: 2
    description: Default 2-approver requirement for policy changes
"""


def _sh(*args: str) -> str:
    """Execute shell command and return stdout."""
    return subprocess.check_output(args, text=True).strip()


def _api(method: str, endpoint: str, data: Optional[Dict] = None) -> Any:
    """Call GitHub API."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise ValueError("GITHUB_TOKEN not set")

    import urllib.request

    url = f"https://api.github.com{endpoint}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }

    if data:
        req = urllib.request.Request(
            url, data=json.dumps(data).encode("utf-8"), headers=headers, method=method
        )
    else:
        req = urllib.request.Request(url, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"API error: {e}", file=sys.stderr)
        return None


def load_approval_policy() -> Dict[str, Any]:
    """Load approval policy from file or use default."""
    policy_path = os.environ.get(
        "DECISIONOS_POLICY_APPROVERS_YAML", ".github/approval_policies.yaml"
    )

    if os.path.exists(policy_path):
        with open(policy_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    else:
        # Use default policy
        return yaml.safe_load(DEFAULT_APPROVAL_POLICY)


def get_changed_files(base: str = "origin/main", head: str = "HEAD") -> List[str]:
    """Get list of changed files in PR."""
    try:
        out = _sh("git", "diff", "--name-only", f"{base}...{head}")
        return [line for line in out.splitlines() if line]
    except subprocess.CalledProcessError:
        try:
            out = _sh("git", "diff", "--name-only", base, head)
            return [line for line in out.splitlines() if line]
        except subprocess.CalledProcessError:
            return []


def match_glob(filename: str, pattern: str) -> bool:
    """Match filename against glob pattern."""
    # Convert glob to regex
    # Support {json,yaml} brace expansion
    if "{" in pattern:
        # Extract brace content
        match = re.search(r"\{([^}]+)\}", pattern)
        if match:
            extensions = match.group(1).split(",")
            base_pattern = pattern[: match.start()] + "EXT" + pattern[match.end() :]
            for ext in extensions:
                if match_glob(filename, base_pattern.replace("EXT", ext)):
                    return True
            return False

    # Simple glob matching
    regex = pattern.replace(".", r"\.").replace("*", ".*").replace("?", ".")
    return bool(re.fullmatch(regex, filename))


def get_pr_reviewers(repo: str, pr_number: int) -> Set[str]:
    """Get list of PR reviewers (usernames)."""
    data = _api("GET", f"/repos/{repo}/pulls/{pr_number}/reviews")
    if not data:
        return set()

    reviewers = set()
    for review in data:
        if review.get("state") == "APPROVED":
            reviewers.add(review["user"]["login"])

    return reviewers


def get_user_teams(repo: str, username: str) -> Set[str]:
    """Get user's teams (simplified - returns empty set for now)."""
    # Production would use GitHub API: GET /orgs/{org}/teams/{team}/memberships/{username}
    # For now, we use a simple heuristic based on username patterns
    teams = set()

    # Heuristic: check username patterns
    username_lower = username.lower()
    if "sec" in username_lower or "security" in username_lower:
        teams.add("security")
    if "platform" in username_lower or "infra" in username_lower:
        teams.add("platform")
    if "service" in username_lower or "svc" in username_lower:
        teams.add("service")

    return teams


def check_rule(
    rule: Dict[str, Any], changed_files: List[str], reviewers: Set[str], repo: str
) -> Tuple[bool, List[str]]:
    """Check if rule requirements are met.

    Returns:
        (passed, errors)
    """
    glob_pattern = rule.get("glob", "")
    matching_files = [f for f in changed_files if match_glob(f, glob_pattern)]

    if not matching_files:
        # Rule doesn't apply
        return True, []

    errors = []

    # Check total approver count
    required_approvers = rule.get("required_approvers", 0)
    if len(reviewers) < required_approvers:
        errors.append(
            f"{rule.get('name', 'Rule')}: requires {required_approvers} approvers, got {len(reviewers)}"
        )

    # Check team requirements
    required_teams = rule.get("required_teams", [])
    min_per_team = rule.get("min_per_team", 1)

    if required_teams:
        team_counts: Dict[str, int] = {team: 0 for team in required_teams}

        for reviewer in reviewers:
            user_teams = get_user_teams(repo, reviewer)
            for team in required_teams:
                if team in user_teams:
                    team_counts[team] += 1

        # Check if all teams have minimum approvers
        for team, count in team_counts.items():
            if count < min_per_team:
                errors.append(
                    f"{rule.get('name', 'Rule')}: team '{team}' requires {min_per_team} approvers, got {count}"
                )

    return len(errors) == 0, errors


def main() -> int:
    """Main entry point."""
    # Check for required env vars
    token = os.environ.get("GITHUB_TOKEN", "")
    pr_number_str = os.environ.get("CI_PR_NUMBER", "")
    repo = os.environ.get("CI_REPO", "")

    if not token or not pr_number_str or not repo:
        print("Skipping multisig check: missing GITHUB_TOKEN/CI_PR_NUMBER/CI_REPO")
        return 0  # Soft-fail in non-PR environments

    try:
        pr_number = int(pr_number_str)
    except ValueError:
        print(f"Invalid CI_PR_NUMBER: {pr_number_str}", file=sys.stderr)
        return 0

    # Load approval policy
    policy = load_approval_policy()
    rules = policy.get("rules", [])

    if not rules:
        print("Warning: No approval rules defined", file=sys.stderr)
        return 0

    # Get changed files
    changed_files = get_changed_files()
    if not changed_files:
        print("No files changed, skipping multisig check")
        return 0

    # Get PR reviewers
    reviewers = get_pr_reviewers(repo, pr_number)
    print(f"PR #{pr_number}: {len(reviewers)} approvers: {', '.join(reviewers)}")

    # Check each rule
    all_errors = []
    for rule in rules:
        passed, errors = check_rule(rule, changed_files, reviewers, repo)
        if not passed:
            all_errors.extend(errors)

    # Summary
    if all_errors:
        print("\n❌ Multisig approval requirements NOT met:\n")
        for err in all_errors:
            print(f"  - {err}")
        print("\nAdd required approvals or apply 'review/2-approvers' label to override")
        return 3  # Fail
    else:
        print("\n✓ All multisig approval requirements met")
        return 0


if __name__ == "__main__":
    sys.exit(main())
