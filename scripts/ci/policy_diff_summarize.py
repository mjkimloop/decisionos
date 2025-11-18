#!/usr/bin/env python3
"""Policy diff summarizer: Extract critical field changes from signed policy JSON.

Outputs:
- MD summary (table format) -> var/gate/policy-diff-*.md
- JSON summary (structured) -> var/gate/policy-diff-*.json

Critical fields tracked:
- budget.allow_levels, budget.max_spent
- quota.forbid_actions
- latency.max_p95_ms, latency.max_p99_ms
- error.max_error_rate
- min_samples, window_sec, grace_burst
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

CRITICAL = [
    ("budget", "allow_levels"),
    ("budget", "max_spent"),
    ("quota", "forbid_actions"),
    ("latency", "max_p95_ms"),
    ("latency", "max_p99_ms"),
    ("error", "max_error_rate"),
    ("min_samples",),
    ("window_sec",),
    ("grace_burst",),
]


def _sh(*args: str) -> str:
    """Execute shell command and return stdout."""
    return subprocess.check_output(args, text=True).strip()


def load_json_at_commit(path: str, ref: str) -> Dict[str, Any]:
    """Load JSON file content at specific git commit."""
    blob = _sh("git", "show", f"{ref}:{path}")
    return json.loads(blob)


def pick(data: Dict[str, Any], path: Tuple[str, ...]) -> Any:
    """Extract nested value from dict by path tuple."""
    cur = data
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur


def summarize(path: str, base: str, head: str) -> Tuple[str, Dict[str, Any]]:
    """Generate diff summary for policy file.

    Returns:
        (markdown_table, json_summary)
    """
    try:
        before = load_json_at_commit(path, base)
        after = load_json_at_commit(path, head)
    except subprocess.CalledProcessError:
        # File doesn't exist at one of the commits
        return "", {"file": path, "changes": []}

    md_lines = ["### Policy Diff (critical fields)\n\n", "|field|before|after|\n", "|---|---:|---:|\n"]
    changes = []

    for field_path in CRITICAL:
        val_before = pick(before, field_path)
        val_after = pick(after, field_path)

        if val_before != val_after:
            key = ".".join(field_path)
            changes.append({"field": key, "before": val_before, "after": val_after})
            md_lines.append(f"|`{key}`|`{val_before}`|`{val_after}`|\n")

    json_summary = {"file": path, "changes": changes}
    return "".join(md_lines), json_summary


def main() -> int:
    """Main entry point."""
    base = os.environ.get("CI_BASE_SHA") or os.environ.get("GITHUB_BASE_SHA") or "origin/main"
    head = os.environ.get("CI_HEAD_SHA") or os.environ.get("GITHUB_SHA") or "HEAD"
    glob_pat = os.environ.get("POLICY_GLOB", "configs/policy/*.signed.json")
    out_dir = os.environ.get("OUT_DIR", "var/gate")

    os.makedirs(out_dir, exist_ok=True)

    any_output = False

    for path in glob.glob(glob_pat):
        try:
            md, js = summarize(path, base, head)

            if not js["changes"]:
                continue

            any_output = True

            # Write MD summary
            basename = os.path.basename(path)
            md_path = os.path.join(out_dir, f"policy-diff-{basename}.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md)

            # Write JSON summary
            json_path = os.path.join(out_dir, f"policy-diff-{basename}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(js, f, ensure_ascii=False, indent=2)

            print(f"diff summary: {path}")

        except Exception as e:
            print(f"skip {path}: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
