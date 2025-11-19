import json
from fastapi.testclient import TestClient

from apps.ops.api.server import app as ops_app


def test_cards_delta_304_with_cached_etag(monkeypatch, tmp_path):
    idx = tmp_path / "index.json"
    idx.write_text(json.dumps({"items": []}), encoding="utf-8")
    monkeypatch.setenv("DECISIONOS_EVIDENCE_INDEX", str(idx))
    monkeypatch.setenv("DECISIONOS_CARDS_TTL", "60")
    monkeypatch.setenv("DECISIONOS_RBAC_TEST_MODE", "1")

    c = TestClient(ops_app)
    r1 = c.get("/ops/cards/reason-trends", headers={"X-Scopes": "ops:read"})
    assert r1.status_code == 200
    etag = r1.headers["ETag"]
    r2 = c.get(
        "/ops/cards/reason-trends",
        headers={"If-None-Match": etag, "X-Scopes": "ops:read"},
    )
    assert r2.status_code == 304
    assert r2.headers.get("Content-Length") == "0"
