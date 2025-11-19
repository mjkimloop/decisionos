from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.gateway.routers.consent import router


def build_app():
    app = FastAPI()
    app.include_router(router)
    return app


def test_consent_router_requires_scope(monkeypatch):
    monkeypatch.setenv("DECISIONOS_RBAC_TEST_MODE", "1")
    app = build_app()
    client = TestClient(app)

    # 스코프 없으면 403
    r = client.post("/api/v1/consent/grant", json={"subject_id": "s", "doc_hash": "hash1234", "scope": "a", "ttl_sec": 60})
    assert r.status_code in (401, 403)

    headers = {"X-Scopes": "consent:write"}
    r2 = client.post(
        "/api/v1/consent/grant",
        headers=headers,
        json={"subject_id": "s", "doc_hash": "hash1234", "scope": "a", "ttl_sec": 60},
    )
    assert r2.status_code == 201

    # revoke + list
    r3 = client.get("/api/v1/consent/s", headers={"X-Scopes": "consent:read"})
    assert r3.status_code == 200
    assert isinstance(r3.json(), list)

    r4 = client.post("/api/v1/consent/revoke", headers=headers, json={"subject_id": "s", "doc_hash": "hash1234"})
    assert r4.status_code == 204
