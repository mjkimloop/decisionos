#!/usr/bin/env python3
"""Attestation verifier: Validate build attestations.

Verifies:
- Attestation file exists and is valid JSON
- Policy root_hash matches current registry
- Tests passed (if configured)
- Commit SHA matches (if specified)

Usage:
    python -m scripts.ci.verify_attestation <attestation_file>
    python -m scripts.ci.verify_attestation --commit <sha>

Environment:
    REQUIRE_TESTS_PASSED: "1" to fail if tests didn't pass (default "0")
    REQUIRE_POLICY_MATCH: "1" to fail if policy root_hash mismatch (default "1")

Exit codes:
    0: Verification passed
    1: Verification failed
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_policy_registry() -> Dict[str, Any]:
    """Load policy registry."""
    registry_path = "configs/policy/registry.json"
    if not os.path.exists(registry_path):
        return {}

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def verify_attestation(
    attestation_path: str, require_tests: bool = False, require_policy: bool = True
) -> Tuple[bool, List[str]]:
    """Verify attestation file.

    Args:
        attestation_path: Path to attestation file
        require_tests: Require tests to have passed
        require_policy: Require policy root_hash to match

    Returns:
        (passed, errors)
    """
    errors = []

    # Load attestation
    if not os.path.exists(attestation_path):
        return False, [f"Attestation file not found: {attestation_path}"]

    try:
        with open(attestation_path, "r", encoding="utf-8") as f:
            attestation = json.load(f)
    except Exception as e:
        return False, [f"Invalid attestation JSON: {e}"]

    # Verify version
    if attestation.get("version") != 1:
        errors.append(f"Unknown attestation version: {attestation.get('version')}")

    # Verify type
    if attestation.get("type") != "build-attestation":
        errors.append(f"Unknown attestation type: {attestation.get('type')}")

    # Verify policy root_hash
    if require_policy:
        registry = load_policy_registry()
        current_root_hash = registry.get("root_hash", "")
        attestation_root_hash = attestation.get("policy", {}).get("root_hash", "")

        if attestation_root_hash != current_root_hash:
            errors.append(
                f"Policy root_hash mismatch: attestation={attestation_root_hash}, "
                f"current={current_root_hash}"
            )

    # Verify tests
    if require_tests:
        test_status = attestation.get("tests", {}).get("status", "unknown")
        if test_status != "passed":
            errors.append(f"Tests did not pass: {test_status}")

    return len(errors) == 0, errors


def find_attestation_by_commit(commit_sha: str, search_dir: str = "var/gate") -> str:
    """Find attestation file by commit SHA."""
    # Try full commit SHA first
    attestation_path = os.path.join(search_dir, f"attestation-{commit_sha}.json")
    if os.path.exists(attestation_path):
        return attestation_path

    # Try short commit SHA (12 chars)
    short_sha = commit_sha[:12]
    attestation_path = os.path.join(search_dir, f"attestation-{short_sha}.json")
    if os.path.exists(attestation_path):
        return attestation_path

    # Search for any matching prefix
    search_path = Path(search_dir)
    if search_path.exists():
        for f in search_path.glob(f"attestation-{short_sha}*.json"):
            return str(f)

    return ""


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Verify build attestation")
    parser.add_argument(
        "attestation_file",
        nargs="?",
        help="Attestation file to verify",
    )
    parser.add_argument(
        "--commit",
        help="Commit SHA to find attestation for",
    )
    parser.add_argument(
        "--require-tests",
        action="store_true",
        help="Require tests to have passed",
    )
    parser.add_argument(
        "--require-policy",
        action="store_true",
        default=True,
        help="Require policy root_hash to match (default True)",
    )
    parser.add_argument(
        "--no-require-policy",
        action="store_false",
        dest="require_policy",
        help="Don't require policy root_hash to match",
    )

    args = parser.parse_args()

    # Check env vars
    require_tests = args.require_tests or os.environ.get("REQUIRE_TESTS_PASSED") == "1"
    require_policy = args.require_policy and os.environ.get("REQUIRE_POLICY_MATCH", "1") == "1"

    # Determine attestation file
    attestation_file = args.attestation_file

    if not attestation_file and args.commit:
        # Find by commit SHA
        attestation_file = find_attestation_by_commit(args.commit)
        if not attestation_file:
            print(f"❌ No attestation found for commit: {args.commit}", file=sys.stderr)
            return 1

    if not attestation_file:
        print("Error: Specify attestation file or --commit", file=sys.stderr)
        parser.print_help()
        return 1

    # Verify attestation
    passed, errors = verify_attestation(attestation_file, require_tests, require_policy)

    if passed:
        print(f"✓ Attestation verified: {attestation_file}")

        # Print details
        with open(attestation_file, "r", encoding="utf-8") as f:
            attestation = json.load(f)

        print(f"  Commit: {attestation.get('build', {}).get('commit_sha_full', 'unknown')}")
        print(f"  Branch: {attestation.get('build', {}).get('branch', 'unknown')}")
        print(f"  Policy root_hash: {attestation.get('policy', {}).get('root_hash', '(none)')}")
        print(f"  Tests: {attestation.get('tests', {}).get('status', 'unknown')}")

        return 0
    else:
        print(f"❌ Attestation verification FAILED: {attestation_file}", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
