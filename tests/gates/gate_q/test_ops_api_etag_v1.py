import os
import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.gate_q]

@pytest.fixture(autouse=True)
def rbac_allow(monkeypatch):
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "*")

@pytest.fixture
def client(tmp_path, monkeypatch):
    # Setup evidence index
    idx_path = tmp_path / "index.json"
    idx_path.write_text('{"files":[],"last_updated":1234567890}', encoding="utf-8")
    monkeypatch.setenv("DECISIONOS_EVIDENCE_INDEX", str(idx_path))
    
    from apps.ops.api import API
    return TestClient(API)

def test_reason_trends_etag(client):
    """First request gets 200, second with ETag gets 304"""
    resp1 = client.get("/ops/cards/reason-trends")
    assert resp1.status_code == 200
    assert "ETag" in resp1.headers
    
    etag = resp1.headers["ETag"]
    resp2 = client.get("/ops/cards/reason-trends", headers={"If-None-Match": etag})
    assert resp2.status_code == 304

def test_top_impact_cache_headers(client):
    """Response includes cache control headers"""
    resp = client.get("/ops/cards/top-impact")
    assert resp.status_code == 200
    assert "Cache-Control" in resp.headers
    assert "Surrogate-Control" in resp.headers
    assert "Last-Modified" in resp.headers
