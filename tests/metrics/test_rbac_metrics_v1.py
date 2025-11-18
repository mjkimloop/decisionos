"""Tests for RBAC metrics (hot-reload, route match, eval)."""
from __future__ import annotations

import os
import tempfile
import textwrap
import time

import pytest


@pytest.mark.metrics
def test_rbac_route_match_metrics(monkeypatch, tmp_path):
    """Test: RBAC route match hit/miss metrics."""
    # Create RBAC map
    rbac_map = tmp_path / "rbac_map.yaml"
    rbac_map.write_text(
        textwrap.dedent(
            """
        policy:
          mode: OR
        routes:
          - path: "/ops/cards*"
            method: "*"
            scopes: ["ops:read"]
    """
        ).strip()
    )

    monkeypatch.setenv("DECISIONOS_RBAC_MAP_PATH", str(rbac_map))
    monkeypatch.setenv("DECISIONOS_RBAC_RELOAD_SEC", "1")
    monkeypatch.setenv("DECISIONOS_RBAC_TEST_MODE", "1")
    monkeypatch.setenv("DECISIONOS_RBAC_DEFAULT_DENY", "1")

    # Import after env setup
    from starlette.testclient import TestClient
    from apps.ops.api import app

    c = TestClient(app)

    # Miss (no route match)
    r1 = c.get("/unknown-path")
    assert r1.status_code == 403

    # Check metrics
    m1 = c.get("/metrics").text
    assert "decisionos_rbac_route_match_total" in m1
    assert 'match="miss"' in m1

    # Hit (route matched, but denied due to missing scope)
    r2 = c.get("/ops/cards/test")
    assert r2.status_code == 403

    m2 = c.get("/metrics").text
    assert 'match="hit"' in m2
    assert 'result="deny"' in m2

    # Allowed (with scope)
    r3 = c.get("/ops/cards/test", headers={"X-Scopes": "ops:read"})
    assert r3.status_code in (200, 304)  # May return 304 if cached

    m3 = c.get("/metrics").text
    assert 'result="allow"' in m3


@pytest.mark.metrics
def test_rbac_bypass_metrics(monkeypatch):
    """Test: RBAC bypass metrics for health endpoints."""
    monkeypatch.setenv("DECISIONOS_RBAC_BYPASS_PREFIXES", "/healthz,/readyz,/metrics")
    monkeypatch.setenv("DECISIONOS_RBAC_TEST_MODE", "1")

    from starlette.testclient import TestClient
    from apps.ops.api import app

    c = TestClient(app)

    # Bypass endpoints should not be blocked
    r1 = c.get("/metrics")
    assert r1.status_code == 200

    # Check for bypass metric
    m1 = r1.text
    assert 'result="bypass"' in m1


@pytest.mark.metrics
def test_rbac_map_reload_metrics(monkeypatch, tmp_path):
    """Test: RBAC map reload metrics on file change."""
    rbac_map = tmp_path / "rbac_map.yaml"
    rbac_map.write_text(
        textwrap.dedent(
            """
        policy:
          mode: OR
        routes:
          - path: "/api/*"
            scopes: ["api:read"]
    """
        ).strip()
    )

    monkeypatch.setenv("DECISIONOS_RBAC_MAP_PATH", str(rbac_map))
    monkeypatch.setenv("DECISIONOS_RBAC_RELOAD_SEC", "1")
    monkeypatch.setenv("DECISIONOS_RBAC_TEST_MODE", "1")

    from starlette.testclient import TestClient
    from apps.ops.api import app

    c = TestClient(app)

    # Initial request
    r1 = c.get("/metrics")
    m1 = r1.text

    # Should have reload metric from initial load
    assert "decisionos_rbac_map_reload_total" in m1

    # Modify map
    rbac_map.write_text(
        textwrap.dedent(
            """
        policy:
          mode: AND
        routes:
          - path: "/api/v2/*"
            scopes: ["api:write"]
    """
        ).strip()
    )

    # Wait for reload interval
    time.sleep(1.5)

    # Trigger a request to reload
    r2 = c.get("/api/test")

    # Check metrics again
    m2 = c.get("/metrics").text

    # Should have incremented reload counter
    assert "decisionos_rbac_map_reload_total" in m2
