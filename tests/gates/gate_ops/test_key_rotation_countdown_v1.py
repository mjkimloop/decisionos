"""Tests for key rotation countdown checker."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


@pytest.fixture
def test_keys_healthy():
    """Test keys with healthy expiration dates."""
    now = datetime.now(timezone.utc)
    expires_in_30d = (now + timedelta(days=30)).isoformat()
    grace_in_30d = (now + timedelta(days=30)).isoformat()

    return json.dumps([
        {
            "key_id": "active-k1",
            "secret": "dGVzdC1zZWNyZXQtMQ==",
            "state": "active",
            "expires_at": expires_in_30d
        },
        {
            "key_id": "grace-k2",
            "secret": "dGVzdC1zZWNyZXQtMg==",
            "state": "grace",
            "grace_until": grace_in_30d
        }
    ])


@pytest.fixture
def test_keys_warning():
    """Test keys with warning-level expiration."""
    now = datetime.now(timezone.utc)
    expires_in_5d = (now + timedelta(days=5)).isoformat()

    return json.dumps([
        {
            "key_id": "active-k1",
            "secret": "dGVzdC1zZWNyZXQtMQ==",
            "state": "active",
            "expires_at": expires_in_5d
        }
    ])


@pytest.fixture
def test_keys_critical():
    """Test keys with critical-level expiration."""
    now = datetime.now(timezone.utc)
    expires_in_2d = (now + timedelta(days=2)).isoformat()

    return json.dumps([
        {
            "key_id": "active-k1",
            "secret": "dGVzdC1zZWNyZXQtMQ==",
            "state": "active",
            "expires_at": expires_in_2d
        }
    ])


@pytest.fixture
def test_keys_expired():
    """Test keys with expired grace period."""
    now = datetime.now(timezone.utc)
    expired_5d_ago = (now - timedelta(days=5)).isoformat()

    return json.dumps([
        {
            "key_id": "grace-k1",
            "secret": "dGVzdC1zZWNyZXQtMQ==",
            "state": "grace",
            "grace_until": expired_5d_ago
        }
    ])


@pytest.mark.gate_ops
def test_rotation_countdown_healthy(test_keys_healthy, monkeypatch):
    """Test: Healthy keys pass countdown check."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", test_keys_healthy)

    script = Path("scripts/ops/check_key_rotation_countdown.py")
    result = subprocess.run(
        ["python", str(script), "--warn-days", "7", "--critical-days", "3"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "✓✓✓ All keys healthy ✓✓✓" in result.stdout


@pytest.mark.gate_ops
def test_rotation_countdown_warning(test_keys_warning, monkeypatch):
    """Test: Warning-level expiration triggers warning."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", test_keys_warning)

    script = Path("scripts/ops/check_key_rotation_countdown.py")
    result = subprocess.run(
        ["python", str(script), "--warn-days", "7", "--critical-days", "3"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 1
    assert "⚠⚠⚠ WARNING: Key rotation required soon ⚠⚠⚠" in result.stdout
    assert "Active key expires in 5 days" in result.stdout


@pytest.mark.gate_ops
def test_rotation_countdown_critical(test_keys_critical, monkeypatch):
    """Test: Critical-level expiration triggers critical alert."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", test_keys_critical)

    script = Path("scripts/ops/check_key_rotation_countdown.py")
    result = subprocess.run(
        ["python", str(script), "--warn-days", "7", "--critical-days", "3"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 2
    assert "✗✗✗ CRITICAL: Key rotation required immediately ✗✗✗" in result.stdout
    assert "Active key expires in 2 days (CRITICAL)" in result.stdout


@pytest.mark.gate_ops
def test_rotation_countdown_expired_grace(test_keys_expired, monkeypatch):
    """Test: Expired grace period triggers critical alert."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", test_keys_expired)

    script = Path("scripts/ops/check_key_rotation_countdown.py")
    result = subprocess.run(
        ["python", str(script)],
        capture_output=True,
        text=True
    )

    assert result.returncode == 2
    assert "Grace period EXPIRED" in result.stdout


@pytest.mark.gate_ops
def test_rotation_countdown_no_keys(monkeypatch):
    """Test: No keys configured."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", "[]")

    script = Path("scripts/ops/check_key_rotation_countdown.py")
    result = subprocess.run(
        ["python", str(script)],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "No keys found" in result.stdout


@pytest.mark.gate_ops
def test_rotation_countdown_custom_thresholds(test_keys_warning, monkeypatch):
    """Test: Custom warning/critical thresholds."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", test_keys_warning)

    script = Path("scripts/ops/check_key_rotation_countdown.py")
    result = subprocess.run(
        ["python", str(script), "--warn-days", "10", "--critical-days", "7"],
        capture_output=True,
        text=True
    )

    # Key expires in 5 days, which is below critical threshold of 7
    assert result.returncode == 2
    assert "CRITICAL" in result.stdout


@pytest.mark.gate_ops
def test_rotation_countdown_env_override(test_keys_warning, monkeypatch):
    """Test: Environment variable overrides thresholds."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", test_keys_warning)
    monkeypatch.setenv("ROTATION_WARN_DAYS", "10")
    monkeypatch.setenv("ROTATION_CRITICAL_DAYS", "7")

    script = Path("scripts/ops/check_key_rotation_countdown.py")
    result = subprocess.run(
        ["python", str(script)],
        capture_output=True,
        text=True,
        env={**os.environ}
    )

    assert result.returncode == 2
    assert "Warning threshold: 10 days" in result.stdout
    assert "Critical threshold: 7 days" in result.stdout


@pytest.mark.gate_ops
def test_rotation_countdown_recommended_actions(test_keys_critical, monkeypatch):
    """Test: Recommended actions are printed for critical state."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", test_keys_critical)

    script = Path("scripts/ops/check_key_rotation_countdown.py")
    result = subprocess.run(
        ["python", str(script)],
        capture_output=True,
        text=True
    )

    assert "Recommended actions:" in result.stdout
    assert "Generate new key:" in result.stdout
    assert "Add to DECISIONOS_POLICY_KEYS" in result.stdout
