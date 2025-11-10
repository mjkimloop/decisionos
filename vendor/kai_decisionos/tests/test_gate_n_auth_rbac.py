from __future__ import annotations

from fastapi.testclient import TestClient

from apps.gateway.main import app


client = TestClient(app)
HEADERS_ADMIN = {"X-Api-Key": "dev-key", "X-Role": "admin", "X-Tenant-ID": "demo-tenant"}


def test_oidc_rbac_invites_pat_admin_ui(tmp_path, monkeypatch):
    config = client.get("/api/v1/auth/oidc/config", headers=HEADERS_ADMIN)
    assert config.status_code == 200
    state = config.json()["authorize_url"].split("state=")[-1].split("&")[0]

    callback = client.post(
        "/api/v1/auth/oidc/callback",
        headers=HEADERS_ADMIN,
        json={"code": "demo-code", "state": state},
    )
    assert callback.status_code == 200
    session_id = callback.json()["session_id"]

    session = client.get(f"/api/v1/auth/oidc/session/{session_id}", headers=HEADERS_ADMIN)
    assert session.status_code == 200

    jwks = client.get("/api/v1/auth/oidc/jwks", headers=HEADERS_ADMIN)
    assert jwks.status_code == 200 and "keys" in jwks.json()

    r_assign = client.post(
        "/api/v1/rbac/assign",
        headers=HEADERS_ADMIN,
        json={"user": "alice", "role": "developer"},
    )
    assert r_assign.status_code == 200
    r_list = client.get("/api/v1/rbac/user/alice", headers=HEADERS_ADMIN)
    assert r_list.status_code == 200 and "developer" in r_list.json()["roles"]
    r_check = client.get(
        "/api/v1/rbac/check",
        headers=HEADERS_ADMIN,
        params={"user": "alice", "permission": "packs.deploy"},
    )
    assert r_check.status_code == 200 and r_check.json()["allowed"] is True

    org = client.post(
        "/api/v1/orgs",
        headers=HEADERS_ADMIN,
        json={"name": "GateN Org", "plan": "growth"},
    )
    org_id = org.json()["id"]

    invite = client.post(
        "/api/v1/invites",
        headers=HEADERS_ADMIN,
        json={"org_id": org_id, "email": "user@example.com", "role": "agent"},
    )
    assert invite.status_code == 200
    token = invite.json()["token"]
    invite_list = client.get(
        "/api/v1/invites",
        headers=HEADERS_ADMIN,
        params={"org_id": org_id},
    )
    assert invite_list.status_code == 200 and invite_list.json()
    accept = client.post(
        "/api/v1/invites/accept",
        headers=HEADERS_ADMIN,
        json={"token": token, "user_id": "user123"},
    )
    assert accept.status_code == 200

    pat_create = client.post(
        "/api/v1/pat",
        headers=HEADERS_ADMIN,
        json={"user_id": "user123", "label": "automation"},
    )
    assert pat_create.status_code == 200
    pat_token = pat_create.json()["token"]
    pat_list = client.get(
        "/api/v1/pat",
        headers=HEADERS_ADMIN,
        params={"user_id": "user123"},
    )
    assert pat_list.status_code == 200 and pat_list.json()
    pat_revoke = client.post(
        "/api/v1/pat/revoke",
        headers=HEADERS_ADMIN,
        params={"token": pat_token},
    )
    assert pat_revoke.status_code == 200

    admin_ui = client.get("/admin/console", headers=HEADERS_ADMIN)
    assert admin_ui.status_code == 200
    assert "Admin Console" in admin_ui.text
