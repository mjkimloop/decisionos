import json
import pathlib
import tempfile

from fastapi.testclient import TestClient

from apps.ops.api.server import app


def _prepare_index(tmp_path: pathlib.Path):
    idx = {"generated_at": "2025-11-18T06:00:00Z", "items": []}
    p = tmp_path / "index.json"
    p.write_text(json.dumps(idx), encoding="utf-8")
    return p


def test_cards_rbac_forbidden_without_scope(monkeypatch, tmp_path):
    idx = _prepare_index(tmp_path)
    monkeypatch.setenv("DECISIONOS_EVIDENCE_INDEX", str(idx))
    monkeypatch.setenv("DECISIONOS_RBAC_TEST_MODE", "1")
    c = TestClient(app)
    r = c.get("/ops/cards/reason-trends?period=1d")
    assert r.status_code == 403


def test_cards_304_and_vary(monkeypatch, tmp_path):
    idx = _prepare_index(tmp_path)
    monkeypatch.setenv("DECISIONOS_EVIDENCE_INDEX", str(idx))
    monkeypatch.setenv("DECISIONOS_RBAC_TEST_MODE", "1")
    c = TestClient(app)
    r1 = c.get("/ops/cards/reason-trends?period=1d", headers={"X-Scopes": "ops:read"})
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    assert etag
    r2 = c.get(
        "/ops/cards/reason-trends?period=1d",
        headers={"X-Scopes": "ops:read", "If-None-Match": etag},
    )
    assert r2.status_code == 304
    assert r2.headers.get("Content-Length") in ("0", None)
    assert "Vary" in r2.headers
