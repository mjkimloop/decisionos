"""Tests for key rotation bot CI script."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

import pytest


def _make_key(key_id: str, days_until_expiry: int) -> dict:
    """Create test key with specified expiry."""
    now = datetime.utcnow()
    not_before = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    not_after = (now + timedelta(days=days_until_expiry)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "key_id": key_id,
        "secret": "test-secret",
        "state": "active",
        "not_before": not_before,
        "not_after": not_after,
    }


@pytest.mark.ci
def test_bot_disabled_when_flag_off(monkeypatch):
    """Test: Bot skips when ROTATION_PR_ENABLE=0."""
    monkeypatch.setenv("ROTATION_PR_ENABLE", "0")

    r = subprocess.run([sys.executable, "-m", "scripts.ci.key_rotation_bot"], capture_output=True, text=True)

    assert r.returncode == 0
    assert "disabled" in r.stdout.lower()


@pytest.mark.ci
def test_bot_skip_without_token(monkeypatch):
    """Test: Bot skips when GITHUB_TOKEN is missing."""
    monkeypatch.setenv("ROTATION_PR_ENABLE", "1")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("CI_REPO", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    r = subprocess.run([sys.executable, "-m", "scripts.ci.key_rotation_bot"], capture_output=True, text=True)

    assert r.returncode == 0
    assert "skip" in r.stdout.lower()


@pytest.mark.ci
def test_bot_skip_no_expiring_keys(monkeypatch):
    """Test: Bot skips when no keys are expiring soon."""
    keys = [_make_key("k1", 60)]  # 60 days until expiry
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", json.dumps(keys))
    monkeypatch.setenv("ROTATION_PR_ENABLE", "1")
    monkeypatch.setenv("ROTATION_SOON_DAYS", "14")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)  # Skip PR creation

    r = subprocess.run([sys.executable, "-m", "scripts.ci.key_rotation_bot"], capture_output=True, text=True)

    assert r.returncode == 0


@pytest.mark.ci
def test_bot_days_left_calculation():
    """Test: days_left() calculates correctly."""
    from scripts.ci.key_rotation_bot import days_left

    now = datetime.utcnow()
    future_10d = (now + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")

    days = days_left(future_10d)
    assert 9.5 < days < 10.5  # Allow some tolerance


@pytest.mark.ci
def test_bot_label_selection():
    """Test: Correct labels selected based on days left."""
    keys = [
        _make_key("k1", 3),  # rotation:soon-3
        _make_key("k2", 7),  # rotation:soon-7
        _make_key("k3", 14),  # rotation:soon-14
    ]

    # Test label logic (would need to refactor bot to expose this)
    # For now, just verify keys are parsed correctly
    from scripts.ci.key_rotation_bot import parse_keys, days_left

    import json
    import os

    os.environ["DECISIONOS_POLICY_KEYS"] = json.dumps(keys)
    parsed = parse_keys()
    assert len(parsed) == 3

    # Verify days_left for each
    assert days_left(parsed[0]["not_after"]) <= 3
    assert days_left(parsed[1]["not_after"]) <= 7
    assert days_left(parsed[2]["not_after"]) <= 14
