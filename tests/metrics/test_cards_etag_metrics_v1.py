from starlette.testclient import TestClient

from apps.ops.api.server import app


def test_etag_metric_increments(monkeypatch, tmp_path):
    idx = tmp_path / "index.json"
    idx.write_text('{"buckets":[],"generated_at":"2025-11-18T00:00:00Z"}', encoding="utf-8")
    monkeypatch.setenv("DECISIONOS_EVIDENCE_INDEX", str(idx))
    monkeypatch.setenv("DECISIONOS_RBAC_TEST_MODE", "1")
    c = TestClient(app)
    h = {"X-Scopes": "ops:read"}
    _ = c.get("/ops/cards/reason-trends", headers=h)
    r = c.get("/metrics")
    body = r.text
    assert "decisionos_cards_etag_total" in body
