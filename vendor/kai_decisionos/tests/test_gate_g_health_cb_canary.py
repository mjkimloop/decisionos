from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from apps.gateway.main import app
from apps.common.circuit import CircuitBreaker
from apps.switchboard.router import Router


client = TestClient(app)
HEADERS = {"X-Api-Key": "dev-key", "X-Role": "admin", "X-Tenant-ID": "demo-tenant"}


def test_health_live_ready_and_degrade():
    r = client.get("/api/v1/health/live", headers=HEADERS)
    assert r.status_code == 200 and r.json().get("ok") is True
    r2 = client.get("/api/v1/health/ready", headers=HEADERS)
    assert r2.status_code == 200 and r2.json().get("ok") is True
    client.post("/api/v1/health/degrade/on", headers=HEADERS)
    r3 = client.get("/api/v1/health/ready", headers=HEADERS)
    assert r3.status_code == 200 and r3.json().get("ok") is False
    client.post("/api/v1/health/degrade/off", headers=HEADERS)


def test_circuit_breaker_opens_and_resets():
    cb = CircuitBreaker(failure_threshold=2, reset_timeout=0.1)
    assert cb.is_open() is False
    cb.record_failure(); cb.record_failure()
    assert cb.is_open() is True
    # simulate timeout expiry
    import time
    time.sleep(0.11)
    assert cb.is_open() is False


def test_router_canary_and_chaos():
    r = Router()
    out = asyncio.run(r.route("hello", capability="default", cost_budget=1.0, timeout=0.5, canary_percent=1.0))
    assert out["meta"].get("canary") is True
    # chaos forces error -> fallback to local
    out2 = asyncio.run(r.route("hello", capability="default", cost_budget=1.0, timeout=0.5, chaos=True))
    assert out2["meta"]["fallback_reason"] in {"error", "timeout", "cost"}

