from __future__ import annotations

from fastapi.testclient import TestClient

from apps.gateway.main import app

client = TestClient(app)


def test_missing_tenant_header_returns_400():
    r = client.get('/health', headers={"X-Api-Key": "dev-key", "X-Role": "admin"})
    assert r.status_code == 400


def test_wrong_tenant_header_returns_403():
    r = client.get('/health', headers={"X-Api-Key": "dev-key", "X-Role": "admin", "X-Tenant-ID": "wrong"})
    assert r.status_code == 403


def test_correct_tenant_header_ok():
    r = client.get('/health', headers={"X-Api-Key": "dev-key", "X-Role": "admin", "X-Tenant-ID": "demo-tenant"})
    assert r.status_code == 200 and r.json().get('ok') is True
