from __future__ import annotations

from fastapi.testclient import TestClient

from apps.gateway.main import app
from apps.providers.v2.openai_mock import OpenAIMockV2


client = TestClient(app)
HEADERS = {"X-Api-Key": "dev-key", "X-Role": "admin", "X-Tenant-ID": "demo-tenant"}


def test_correlation_header_roundtrip():
    h = dict(HEADERS)
    h["X-Corr-Id"] = "corr-abc"
    r = client.get("/api/v1/health/ready", headers=h)
    assert r.status_code == 200
    assert r.headers.get("X-Corr-Id") == "corr-abc"


def test_admin_metrics_contains_cost_and_app_metrics():
    # ensure a decision to produce route meta and cost
    payload = {"org_id": "orgA", "payload": {"credit_score": 720, "dti": 0.3, "income_verified": True}}
    d = client.post("/api/v1/decide/lead_triage", headers=HEADERS, json=payload)
    assert d.status_code == 200
    r = client.get("/api/v1/admin/metrics", headers=HEADERS, params={"org_id": "orgA"})
    assert r.status_code == 200
    body = r.json()
    assert "app_metrics" in body and "cost_sentry" in body
    assert body["cost_sentry"].get("total", 0.0) >= 0.0


def test_provider_v2_mock():
    p = OpenAIMockV2()
    out = p.infer({"prompt": "hello world"})
    assert out.get("result", "").startswith("mock:")

