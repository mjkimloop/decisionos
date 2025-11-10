from fastapi.testclient import TestClient
from apps.gateway.main import app


def test_openapi_served():
    client = TestClient(app)
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert "paths" in r.json()


def test_decide_and_explain_roundtrip():
    client = TestClient(app)
    payload = {"org_id": "orgA", "payload": {"credit_score": 720, "dti": 0.3, "income_verified": True}}
    r = client.post("/api/v1/decide/lead_triage", json=payload, headers={"Authorization": "Bearer secret-token"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["decision_id"]
    assert body["class"] in {"approve", "review", "reject"}
    r2 = client.get(f"/api/v1/explain/{body['decision_id']}", headers={"Authorization": "Bearer secret-token"})
    assert r2.status_code == 200
    ex = r2.json()
    assert "rules_applied" in ex and "input_hash" in ex


def test_explain_404():
    client = TestClient(app)
    r = client.get("/api/v1/explain/00000000-0000-0000-0000-000000000000", headers={"Authorization": "Bearer secret-token"})
    assert r.status_code == 404

