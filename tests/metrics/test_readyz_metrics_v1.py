"""Tests for readyz window metrics (status, reason codes)."""
from __future__ import annotations

import pytest


@pytest.mark.metrics
def test_readyz_status_metrics():
    """Test: Readyz status metrics are recorded."""
    from starlette.testclient import TestClient
    from apps.judge.server import app

    c = TestClient(app)

    # Healthy readyz
    r1 = c.get("/readyz")

    # Check metrics
    m1 = c.get("/metrics").text

    assert "decisionos_readyz_total" in m1
    # Should have either ready or degraded
    assert 'result="ready"' in m1 or 'result="degraded"' in m1


@pytest.mark.metrics
def test_readyz_reason_metrics(monkeypatch):
    """Test: Readyz failure reasons are recorded."""
    # Simulate key check failure
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS_JSON", "[]")  # Empty keys

    from starlette.testclient import TestClient
    from apps.judge.server import app

    c = TestClient(app)

    # Degraded readyz (no keys)
    r1 = c.get("/readyz?explain=1")

    # Should be degraded
    data = r1.json()
    assert data["status"] == "degraded"

    # Check metrics for reason codes
    m1 = c.get("/metrics").text

    assert "decisionos_readyz_reason_total" in m1
    # Should have keys check failure
    assert 'check="keys"' in m1


@pytest.mark.metrics
def test_readyz_window_multiple_checks(monkeypatch):
    """Test: Multiple readyz checks accumulate metrics."""
    from starlette.testclient import TestClient
    from apps.judge.server import app

    c = TestClient(app)

    # Multiple requests
    for _ in range(3):
        c.get("/readyz")

    # Check metrics
    m = c.get("/metrics").text

    # Should have accumulated counts
    assert "decisionos_readyz_total" in m


@pytest.mark.metrics
def test_readyz_bypass_metrics_endpoint():
    """Test: /metrics endpoint bypasses RBAC."""
    from starlette.testclient import TestClient
    from apps.judge.server import app

    c = TestClient(app)

    # Metrics should always be accessible
    r = c.get("/metrics")
    assert r.status_code == 200
    assert "decisionos_readyz_total" in r.text
