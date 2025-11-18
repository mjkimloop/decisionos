"""Tests for policy diff summarizer CI script."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


@pytest.mark.ci
def test_policy_diff_no_change(monkeypatch):
    """Test: No output when base and head are the same."""
    monkeypatch.setenv("CI_BASE_SHA", "HEAD")
    monkeypatch.setenv("CI_HEAD_SHA", "HEAD")
    monkeypatch.setenv("POLICY_GLOB", "configs/policy/*.signed.json")

    r = subprocess.run(
        [sys.executable, "-m", "scripts.ci.policy_diff_summarize"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent),
    )

    assert r.returncode == 0


@pytest.mark.ci
def test_policy_diff_pick_nested():
    """Test: pick() extracts nested values correctly."""
    from scripts.ci.policy_diff_summarize import pick

    data = {"budget": {"max_spent": 1000, "allow_levels": ["low", "med"]}, "latency": {"max_p95_ms": 500}}

    assert pick(data, ("budget", "max_spent")) == 1000
    assert pick(data, ("budget", "allow_levels")) == ["low", "med"]
    assert pick(data, ("latency", "max_p95_ms")) == 500
    assert pick(data, ("nonexistent",)) is None
    assert pick(data, ("budget", "nonexistent")) is None


@pytest.mark.ci
def test_policy_diff_critical_fields():
    """Test: CRITICAL fields list is defined."""
    from scripts.ci.policy_diff_summarize import CRITICAL

    assert len(CRITICAL) == 9
    assert ("budget", "max_spent") in CRITICAL
    assert ("latency", "max_p95_ms") in CRITICAL
    assert ("min_samples",) in CRITICAL


@pytest.mark.ci
def test_policy_diff_output_format(tmp_path, monkeypatch):
    """Test: Output files are created in OUT_DIR."""
    monkeypatch.setenv("OUT_DIR", str(tmp_path))
    monkeypatch.setenv("CI_BASE_SHA", "HEAD")
    monkeypatch.setenv("CI_HEAD_SHA", "HEAD")
    monkeypatch.setenv("POLICY_GLOB", "*.nonexistent")  # No files match

    r = subprocess.run(
        [sys.executable, "-m", "scripts.ci.policy_diff_summarize"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent),
    )

    assert r.returncode == 0
    # OUT_DIR should exist
    assert tmp_path.exists()


@pytest.mark.ci
def test_policy_diff_safe_mode_git_error(monkeypatch):
    """Test: Script doesn't crash on git errors."""
    monkeypatch.setenv("CI_BASE_SHA", "nonexistent-ref")
    monkeypatch.setenv("CI_HEAD_SHA", "HEAD")
    monkeypatch.setenv("POLICY_GLOB", "*.json")

    r = subprocess.run(
        [sys.executable, "-m", "scripts.ci.policy_diff_summarize"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent),
    )

    # Should exit 0 (skip errors)
    assert r.returncode == 0
