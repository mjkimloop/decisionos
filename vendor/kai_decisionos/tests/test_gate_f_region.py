from __future__ import annotations

from fastapi.testclient import TestClient

from apps.gateway.main import app

client = TestClient(app)
HEADERS = {"X-Api-Key": "dev-key", "X-Role": "admin", "X-Tenant-ID": "demo-tenant"}


def test_region_status_and_promote(tmp_path):
    r = client.get('/api/v1/region/status', headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert 'active' in data
    # promote to a different name
    p = client.post('/api/v1/region/promote', headers=HEADERS, params={"to": "region-x"})
    assert p.status_code == 200
    r2 = client.get('/api/v1/region/status', headers=HEADERS)
    assert r2.json().get('active') == 'region-x'
