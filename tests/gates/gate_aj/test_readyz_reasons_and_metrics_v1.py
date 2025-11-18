import pytest
from apps.judge.readyz import ReadyzChecks, build_readyz_router
from apps.judge.metrics_readyz import ReadyzMetrics
from fastapi.testclient import TestClient
from fastapi import FastAPI

pytestmark = pytest.mark.gate_aj

def test_readyz_checks_all_ok():
    """모든 체크 통과"""
    checks = ReadyzChecks(
        multikey_fresh=lambda: (True, "multikey.ok", {"count": 2}),
        replay_ping=lambda: (True, "replay.ok", {}),
        clock_ok=lambda: (True, "clock.ok", {"skew": 0}),
        storage_ping=lambda: (True, "storage.ok", {}),
    )
    
    result = checks.run()
    
    assert result["ok"] is True
    assert "checks" in result
    assert result["checks"]["multikey_fresh"]["ok"] is True
    assert result["checks"]["multikey_fresh"]["reason"] == "multikey.ok"
    assert result["checks"]["multikey_fresh"]["metrics"]["count"] == 2

def test_readyz_checks_one_fail():
    """한 체크 실패"""
    checks = ReadyzChecks(
        multikey_fresh=lambda: (False, "multikey.stale", {"age": 100000}),
        replay_ping=lambda: (True, "replay.ok", {}),
        clock_ok=lambda: (True, "clock.ok", {}),
        storage_ping=lambda: (True, "storage.ok", {}),
    )
    
    result = checks.run()
    
    assert result["ok"] is False
    assert result["checks"]["multikey_fresh"]["ok"] is False
    assert result["checks"]["multikey_fresh"]["reason"] == "multikey.stale"

def test_readyz_checks_legacy_bool():
    """레거시 bool 반환 호환성"""
    checks = ReadyzChecks(
        multikey_fresh=lambda: True,
        replay_ping=lambda: False,
        clock_ok=lambda: True,
        storage_ping=lambda: True,
    )

    result = checks.run()

    assert result["checks"]["multikey_fresh"]["ok"] is True
    assert result["checks"]["multikey_fresh"]["reason"] == "ok"
    assert result["checks"]["replay_store"]["ok"] is False
    assert result["checks"]["replay_store"]["reason"] == "replay_store.failed"

def test_readyz_router_fail_closed():
    """fail-closed 모드에서 503 반환"""
    checks = ReadyzChecks(
        multikey_fresh=lambda: (False, "multikey.fail", {}),
        replay_ping=lambda: True,
        clock_ok=lambda: True,
        storage_ping=lambda: True,
    )
    
    router = build_readyz_router(checks, fail_closed=True)
    app = FastAPI()
    app.include_router(router)
    
    client = TestClient(app)
    response = client.get("/readyz")
    
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["ok"] is False

def test_readyz_router_soft_mode():
    """soft 모드에서 200 반환"""
    checks = ReadyzChecks(
        multikey_fresh=lambda: (False, "multikey.fail", {}),
        replay_ping=lambda: True,
        clock_ok=lambda: True,
        storage_ping=lambda: True,
    )
    
    router = build_readyz_router(checks, fail_closed=False)
    app = FastAPI()
    app.include_router(router)
    
    client = TestClient(app)
    response = client.get("/readyz")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"

def test_readyz_metrics_observation():
    """메트릭 관측 테스트"""
    metrics = ReadyzMetrics()
    
    initial = metrics.snapshot()
    assert initial["total"] == 0
    
    metrics.observe(ok=True)
    snapshot = metrics.snapshot()
    assert snapshot["total"] == 1
    assert snapshot["fail"] == 0
    assert snapshot["last_status"] == "ready"
    
    metrics.observe(ok=False)
    snapshot = metrics.snapshot()
    assert snapshot["total"] == 2
    assert snapshot["fail"] == 1
    assert snapshot["last_status"] == "degraded"
