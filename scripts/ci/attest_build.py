#!/usr/bin/env python3
"""Build attestation generator: SBOM hash + policy root_hash.

Generates attestation file with:
- Build metadata (timestamp, commit, branch)
- Policy root_hash from registry
- SBOM hash (if available)
- Test results summary

Usage:
    python -m scripts.ci.attest_build

Environment:
    CI_COMMIT_SHA: Git commit SHA
    CI_BRANCH: Git branch name
    OUT_DIR: Output directory (default: var/gate)

Output:
    var/gate/attestation-{sha}.json
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ISO = "%Y-%m-%dT%H:%M:%SZ"


def _sh(*args: str) -> str:
    """Execute shell command and return stdout."""
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        return ""


def _sha256_file(path: str) -> str:
    """Compute SHA256 hash of file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def get_git_metadata() -> Dict[str, str]:
    """Get git metadata for build."""
    commit_sha = os.environ.get("CI_COMMIT_SHA") or _sh("git", "rev-parse", "HEAD")
    branch = os.environ.get("CI_BRANCH") or _sh("git", "rev-parse", "--abbrev-ref", "HEAD")
    commit_msg = _sh("git", "log", "-1", "--pretty=%s")
    author = _sh("git", "log", "-1", "--pretty=%an <%ae>")

    return {
        "commit_sha": commit_sha[:12],
        "commit_sha_full": commit_sha,
        "branch": branch,
        "commit_message": commit_msg,
        "author": author,
    }


def get_policy_root_hash() -> str:
    """Get root_hash from policy registry."""
    registry_path = "configs/policy/registry.json"
    if not os.path.exists(registry_path):
        return ""

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
        return registry.get("root_hash", "")
    except Exception:
        return ""


def get_sbom_hash() -> str:
    """Get hash of SBOM file if exists."""
    # Check common SBOM locations
    sbom_paths = [
        "var/sbom.json",
        "var/gate/sbom.json",
        "sbom.json",
    ]

    for path in sbom_paths:
        if os.path.exists(path):
            return _sha256_file(path)

    return ""


def collect_test_results() -> Dict[str, Any]:
    """Collect test results from gate directory."""
    gate_dir = Path("var/gate")
    if not gate_dir.exists():
        return {"status": "unknown"}

    # Look for test result files
    result_files = list(gate_dir.glob("test-results-*.json"))
    if not result_files:
        return {"status": "unknown"}

    # Parse latest result file
    latest = max(result_files, key=lambda p: p.stat().st_mtime)
    try:
        with open(latest, "r", encoding="utf-8") as f:
            results = json.load(f)
        return {
            "status": results.get("status", "unknown"),
            "passed": results.get("passed", 0),
            "failed": results.get("failed", 0),
            "skipped": results.get("skipped", 0),
        }
    except Exception:
        return {"status": "error"}


def generate_attestation() -> Dict[str, Any]:
    """Generate build attestation."""
    git_meta = get_git_metadata()

    attestation = {
        "version": 1,
        "type": "build-attestation",
        "created_at": datetime.now(timezone.utc).strftime(ISO),
        "build": {
            **git_meta,
            "timestamp": datetime.now(timezone.utc).strftime(ISO),
        },
        "policy": {
            "root_hash": get_policy_root_hash(),
        },
        "sbom": {
            "hash": get_sbom_hash(),
        },
        "tests": collect_test_results(),
    }

    return attestation


def main() -> int:
    """Main entry point."""
    out_dir = os.environ.get("OUT_DIR", "var/gate")
    os.makedirs(out_dir, exist_ok=True)

    # Generate attestation
    attestation = generate_attestation()

    # Determine output filename
    commit_sha = attestation["build"]["commit_sha"]
    out_path = os.path.join(out_dir, f"attestation-{commit_sha}.json")

    # Write attestation
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(attestation, f, indent=2, ensure_ascii=False)

    print(f"✓ Attestation generated: {out_path}")
    print(f"  Commit: {attestation['build']['commit_sha_full']}")
    print(f"  Policy root_hash: {attestation['policy']['root_hash'] or '(none)'}")
    print(f"  SBOM hash: {attestation['sbom']['hash'] or '(none)'}")
    print(f"  Tests: {attestation['tests'].get('status', 'unknown')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
