from __future__ import annotations

from fastapi.testclient import TestClient

from apps.gateway.main import app

client = TestClient(app)

HEADERS = {"X-Api-Key": "dev-key", "X-Role": "admin", "X-Tenant-ID": "demo-tenant"}


def test_metrics_health_and_payload():
    r = client.get("/api/v1/metrics/healthz", headers=HEADERS)
    assert r.status_code == 200
    r2 = client.get("/api/v1/metrics", headers=HEADERS)
    assert r2.status_code == 200
    data = r2.json().get("metrics", {})
    assert "p95_ms" in data and "error_rate" in data and "req_count" in data


def test_consent_e2e_and_explain_snapshot():
    # grant
    g = client.post(
        "/api/v1/consent/grant",
        headers=HEADERS,
        json={"subject_id": "user1", "doc_hash": "abc", "purpose": "explain", "scope": ["explain"]},
    )
    assert g.status_code == 200
    # list
    lst = client.get("/api/v1/consent/list", headers=HEADERS, params={"subject_id": "user1"})
    assert lst.status_code == 200 and len(lst.json().get("items", [])) >= 1
    # decision to create explain-able id
    payload = {"org_id": "orgA", "payload": {"credit_score": 700, "dti": 0.3, "income_verified": True}}
    d = client.post("/api/v1/decide/lead_triage", headers=HEADERS, json=payload)
    assert d.status_code == 200
    decision_id = d.json()["decision_id"]
    # explain with consent snapshot
    e = client.get(f"/api/v1/explain/{decision_id}", headers=HEADERS, params={"subject_id": "user1"})
    assert e.status_code == 200
    body = e.json()
    assert "consent_snapshot" in body


def test_explain_requires_consent_snapshot():
    payload = {"org_id": "orgB", "payload": {"credit_score": 710, "dti": 0.25, "income_verified": True}}
    d = client.post("/api/v1/decide/lead_triage", headers=HEADERS, json=payload)
    assert d.status_code == 200
    decision_id = d.json()["decision_id"]
    e = client.get(f"/api/v1/explain/{decision_id}", headers=HEADERS, params={"subject_id": "missing-user"})
    assert e.status_code == 403
    assert e.json()["detail"]["error"] == "consent_required"
