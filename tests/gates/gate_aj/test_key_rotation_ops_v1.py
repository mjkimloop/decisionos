"""
키 로테이션 운영 도구 테스트 (v0.5.11r-8)

검증:
- 키 만료 7일 전 경고
- 시계 스큐 ±10초 초과 시 경고
- 무중단 키 교체 (active → grace → retired)
- Grace period 자동 만료
"""
import pytest
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from scripts.ops.key_rotation import (
    check_key_expiry,
    check_clock_skew,
    rotate_key,
    retire_grace_keys,
)

pytestmark = [pytest.mark.gate_aj]


def test_key_expiry_ok():
    """만료 없음 → 정상"""
    now = datetime.now(timezone.utc)
    keys = [
        {
            "key_id": "k1",
            "state": "active",
            "expires_at": (now + timedelta(days=30)).isoformat().replace("+00:00", "Z"),
        }
    ]

    rc = check_key_expiry(keys, warn_days=7)
    assert rc == 0


def test_key_expiry_warn():
    """만료 7일 전 → 경고"""
    now = datetime.now(timezone.utc)
    keys = [
        {
            "key_id": "k1",
            "state": "active",
            "expires_at": (now + timedelta(days=5)).isoformat().replace("+00:00", "Z"),
        }
    ]

    rc = check_key_expiry(keys, warn_days=7)
    assert rc == 1


def test_key_expiry_expired():
    """만료 → 에러"""
    now = datetime.now(timezone.utc)
    keys = [
        {
            "key_id": "k1",
            "state": "active",
            "expires_at": (now - timedelta(days=1)).isoformat().replace("+00:00", "Z"),
        }
    ]

    rc = check_key_expiry(keys, warn_days=7)
    assert rc == 2


def test_key_expiry_no_expires_field():
    """expires_at 없으면 무시"""
    keys = [{"key_id": "k1", "state": "active"}]

    rc = check_key_expiry(keys, warn_days=7)
    assert rc == 0  # 만료 체크 스킵


def test_clock_skew_ok(monkeypatch):
    """시계 스큐 ≤10초 → 정상"""
    monkeypatch.setenv("DECISIONOS_SIMULATED_CLOCK_SKEW_SEC", "5")

    rc = check_clock_skew(max_skew_sec=10)
    assert rc == 0


def test_clock_skew_warn(monkeypatch):
    """시계 스큐 >10초 → 경고"""
    monkeypatch.setenv("DECISIONOS_SIMULATED_CLOCK_SKEW_SEC", "15")

    rc = check_clock_skew(max_skew_sec=10)
    assert rc == 1


def test_clock_skew_negative(monkeypatch):
    """음수 스큐도 감지"""
    monkeypatch.setenv("DECISIONOS_SIMULATED_CLOCK_SKEW_SEC", "-12")

    rc = check_clock_skew(max_skew_sec=10)
    assert rc == 1


def test_rotate_key_active_to_grace():
    """키 로테이션: active → grace"""
    keys = [
        {"key_id": "k1", "state": "active", "secret": "old"},
        {"key_id": "k2", "state": "grace", "secret": "new"},
    ]

    updated = rotate_key(keys, old_key_id="k1", new_key_id="k2", grace_days=7)

    k1 = next(k for k in updated if k["key_id"] == "k1")
    k2 = next(k for k in updated if k["key_id"] == "k2")

    assert k1["state"] == "grace"
    assert "grace_until" in k1
    assert k2["state"] == "active"
    assert "grace_until" not in k2


def test_retire_grace_keys_expired():
    """Grace period 만료 → retired"""
    now = datetime.now(timezone.utc)
    expired_grace = (now - timedelta(days=1)).isoformat().replace("+00:00", "Z")

    keys = [
        {"key_id": "k1", "state": "grace", "grace_until": expired_grace},
    ]

    updated = retire_grace_keys(keys)

    k1 = updated[0]
    assert k1["state"] == "retired"
    assert "grace_until" not in k1


def test_retire_grace_keys_not_expired():
    """Grace period 미만료 → 유지"""
    now = datetime.now(timezone.utc)
    future_grace = (now + timedelta(days=3)).isoformat().replace("+00:00", "Z")

    keys = [
        {"key_id": "k1", "state": "grace", "grace_until": future_grace},
    ]

    updated = retire_grace_keys(keys)

    k1 = updated[0]
    assert k1["state"] == "grace"
    assert k1["grace_until"] == future_grace


def test_rotate_key_missing_old():
    """기존 키 없을 때"""
    keys = [{"key_id": "k2", "state": "grace"}]

    updated = rotate_key(keys, old_key_id="k1", new_key_id="k2")

    # 경고는 나지만 처리 계속
    assert len(updated) == 1


def test_key_rotation_full_lifecycle():
    """전체 라이프사이클: active → grace → retired"""
    now = datetime.now(timezone.utc)

    keys = [
        {"key_id": "k1", "state": "active", "secret": "old"},
        {"key_id": "k2", "state": "pending", "secret": "new"},
    ]

    # 1. 로테이션: k1 active → grace, k2 pending → active
    keys = rotate_key(keys, old_key_id="k1", new_key_id="k2", grace_days=7)

    k1 = next(k for k in keys if k["key_id"] == "k1")
    k2 = next(k for k in keys if k["key_id"] == "k2")

    assert k1["state"] == "grace"
    assert k2["state"] == "active"

    # 2. Grace period 만료 시뮬레이션
    k1["grace_until"] = (now - timedelta(days=1)).isoformat().replace("+00:00", "Z")

    # 3. Retire
    keys = retire_grace_keys(keys)

    k1 = next(k for k in keys if k["key_id"] == "k1")
    assert k1["state"] == "retired"


def test_multiple_keys_different_states():
    """여러 키 동시 관리"""
    now = datetime.now(timezone.utc)

    keys = [
        {"key_id": "k1", "state": "active"},
        {"key_id": "k2", "state": "grace", "grace_until": (now + timedelta(days=3)).isoformat().replace("+00:00", "Z")},
        {"key_id": "k3", "state": "retired"},
    ]

    # Grace 만료 체크
    updated = retire_grace_keys(keys)

    assert len(updated) == 3
    assert updated[0]["state"] == "active"
    assert updated[1]["state"] == "grace"  # 아직 미만료
    assert updated[2]["state"] == "retired"
