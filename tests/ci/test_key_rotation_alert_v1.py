"""Tests for key rotation alert CI script."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

import pytest


def _run_script(env_overrides: dict) -> subprocess.CompletedProcess:
    """Run key_rotation_alert.py with environment overrides."""
    env = os.environ.copy()
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-m", "scripts.ci.key_rotation_alert"],
        capture_output=True,
        text=True,
        env=env,
    )


def _make_key(key_id: str, state: str, days_until_expiry: int) -> dict:
    """Create a test key with specified expiry."""
    now = datetime.utcnow()
    not_before = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    not_after = (now + timedelta(days=days_until_expiry)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "key_id": key_id,
        "secret": "test-secret",
        "state": state,
        "not_before": not_before,
        "not_after": not_after,
    }


@pytest.mark.ci
def test_rotation_alert_ok_no_warnings():
    """Test: No warnings when keys are healthy."""
    keys = [_make_key("k1", "active", 60)]  # 60 days until expiry
    env = {"DECISIONOS_POLICY_KEYS": json.dumps(keys), "ROTATION_SOON_DAYS": "14"}

    r = _run_script(env)
    assert r.returncode == 0, f"Expected exit 0, got {r.returncode}: {r.stdout}"
    rep = json.loads(r.stdout)
    assert rep["summary"]["status"] == "ok"
    assert rep["summary"]["warnings"] == 0


@pytest.mark.ci
def test_rotation_alert_warn_expiry_soon():
    """Test: Warn when key expires soon."""
    keys = [_make_key("k1", "active", 10)]  # 10 days until expiry
    env = {"DECISIONOS_POLICY_KEYS": json.dumps(keys), "ROTATION_SOON_DAYS": "14"}

    r = _run_script(env)
    assert r.returncode == 8, f"Expected exit 8 (warn), got {r.returncode}"
    rep = json.loads(r.stdout)
    assert rep["summary"]["status"] == "warn"
    assert rep["summary"]["warnings"] >= 1
    assert any(f["code"] == "key.expiry_soon" for f in rep["findings"])


@pytest.mark.ci
def test_rotation_alert_warn_insufficient_overlap():
    """Test: Warn when active/grace overlap is insufficient."""
    now = datetime.utcnow()
    # k1: active, expires in 5 days
    k1 = {
        "key_id": "k1",
        "secret": "x",
        "state": "active",
        "not_before": (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "not_after": (now + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    # k2: grace, starts in 3 days (only 2 days overlap with k1)
    k2 = {
        "key_id": "k2",
        "secret": "y",
        "state": "grace",
        "not_before": (now + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "not_after": (now + timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    env = {
        "DECISIONOS_POLICY_KEYS": json.dumps([k1, k2]),
        "GRACE_OVERLAP_DAYS": "7",  # Requires 7 days overlap
    }

    r = _run_script(env)
    assert r.returncode == 8
    rep = json.loads(r.stdout)
    assert rep["summary"]["status"] == "warn"
    assert any(f["code"] == "key.overlap_insufficient" for f in rep["findings"])


@pytest.mark.ci
def test_rotation_alert_empty_keys_ok():
    """Test: Empty keys list is OK (no warnings)."""
    env = {"DECISIONOS_POLICY_KEYS": "[]"}
    r = _run_script(env)
    assert r.returncode == 0
    rep = json.loads(r.stdout)
    assert rep["summary"]["status"] == "ok"


@pytest.mark.ci
def test_rotation_alert_fallback_to_judge_keys():
    """Test: Fallback to DECISIONOS_JUDGE_KEYS if POLICY_KEYS not set."""
    keys = [_make_key("k1", "active", 60)]
    env = {"DECISIONOS_JUDGE_KEYS": json.dumps(keys), "ROTATION_SOON_DAYS": "14"}

    r = _run_script(env)
    assert r.returncode == 0
    rep = json.loads(r.stdout)
    assert rep["summary"]["status"] == "ok"


@pytest.mark.ci
def test_rotation_alert_invalid_json_fails():
    """Test: Invalid JSON fails with error."""
    env = {"DECISIONOS_POLICY_KEYS": "{invalid-json}"}
    r = _run_script(env)
    assert r.returncode != 0
    assert "invalid keys JSON" in r.stderr or "invalid keys JSON" in r.stdout
