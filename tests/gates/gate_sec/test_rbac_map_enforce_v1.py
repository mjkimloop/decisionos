import runpy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.gate_sec]

OPS_API_PATH = Path("apps/ops/api.py")


def _load_ops_app():
    namespace = runpy.run_path(str(OPS_API_PATH), run_name="ops_api_rbac_test")
    return namespace["app"]


def test_rbac_denies_without_scope(monkeypatch):
    monkeypatch.delenv("DECISIONOS_ALLOW_SCOPES", raising=False)
    client = TestClient(_load_ops_app())
    resp = client.get("/ops/cards/reason-trends")
    assert resp.status_code == 403


def test_rbac_allows_with_scope(monkeypatch):
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "ops:read")
    client = TestClient(_load_ops_app())
    resp = client.get("/ops/cards/reason-trends", headers={"x-decisionos-scopes": "ops:read"})
    assert resp.status_code in (200, 404)
