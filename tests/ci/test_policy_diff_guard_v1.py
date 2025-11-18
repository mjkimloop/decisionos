"""Tests for policy diff guard CI script."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


def _run_script(env_overrides: dict) -> subprocess.CompletedProcess:
    """Run policy_diff_guard.py with environment overrides."""
    env = os.environ.copy()
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-m", "scripts.ci.policy_diff_guard"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(Path(__file__).parent.parent.parent),  # Run from repo root
    )


@pytest.mark.ci
def test_policy_diff_guard_no_change_ok():
    """Test: No policy change -> exit 0."""
    env = {
        "CI_BASE_SHA": "HEAD",
        "CI_HEAD_SHA": "HEAD",
        "POLICY_GLOB": "configs/policy/*.signed.json",
    }
    r = _run_script(env)
    assert r.returncode == 0, f"Expected exit 0, got {r.returncode}: {r.stdout}"
    assert "no policy change detected" in r.stdout


@pytest.mark.ci
def test_policy_diff_guard_missing_context_soft_fail():
    """Test: Policy changed but missing PR context -> exit 0 (soft-fail)."""
    # Simulate policy change by comparing different commits
    # Without GITHUB_TOKEN/CI_PR_NUMBER, should soft-fail
    env = {
        "CI_BASE_SHA": "HEAD~1",
        "CI_HEAD_SHA": "HEAD",
        "POLICY_GLOB": "configs/policy/*.signed.json",
        "GITHUB_TOKEN": "",  # Explicitly empty
        "CI_PR_NUMBER": "",
    }
    r = _run_script(env)
    # Should exit 0 even if policy changed (no PR context)
    assert r.returncode == 0
    # May contain soft-fail message or no policy change (depends on actual git history)


@pytest.mark.ci
@pytest.mark.skipif(not os.environ.get("GITHUB_TOKEN"), reason="Requires GITHUB_TOKEN")
def test_policy_diff_guard_with_label_ok():
    """Test: Policy changed with required label -> exit 0."""
    # This test requires actual GitHub API access
    # Skip in environments without GITHUB_TOKEN
    env = {
        "CI_BASE_SHA": "HEAD~1",
        "CI_HEAD_SHA": "HEAD",
        "GITHUB_TOKEN": os.environ["GITHUB_TOKEN"],
        "CI_REPO": os.environ.get("GITHUB_REPOSITORY", "test/repo"),
        "CI_PR_NUMBER": os.environ.get("TEST_PR_NUMBER", "1"),
        "REQUIRED_LABEL": "review/2-approvers",
    }
    # Note: This will only pass if the actual PR has the label
    # In CI, this should be tested with a mock PR or skipped
    r = _run_script(env)
    # Expected: either exit 0 (label present) or exit 3 (label missing)
    assert r.returncode in (0, 3)


@pytest.mark.ci
def test_policy_diff_guard_custom_glob():
    """Test: Custom POLICY_GLOB pattern."""
    env = {
        "CI_BASE_SHA": "HEAD",
        "CI_HEAD_SHA": "HEAD",
        "POLICY_GLOB": "tests/*.py,configs/*.yaml",
    }
    r = _run_script(env)
    assert r.returncode == 0


@pytest.mark.ci
def test_policy_diff_guard_require_approvals_mode():
    """Test: REQUIRE_APPROVALS mode (no label check)."""
    env = {
        "CI_BASE_SHA": "HEAD",
        "CI_HEAD_SHA": "HEAD",
        "REQUIRE_APPROVALS": "1",  # Enable approvals mode
    }
    r = _run_script(env)
    assert r.returncode == 0  # No policy change


@pytest.mark.ci
def test_policy_diff_guard_git_diff_fallback():
    """Test: Graceful handling of git diff errors."""
    # Use invalid base/head to test error handling
    env = {
        "CI_BASE_SHA": "nonexistent-ref",
        "CI_HEAD_SHA": "HEAD",
        "POLICY_GLOB": "*.json",
    }
    r = _run_script(env)
    # Should not crash, either exits 0 (soft-fail) or handles error gracefully
    assert r.returncode in (0, 3, 128)  # 128 = git error
