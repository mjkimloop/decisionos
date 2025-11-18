from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.ops.api import cards_delta


def test_cards_delta_produces_delta(monkeypatch):
    monkeypatch.setenv("DECISIONOS_RBAC_TEST_MODE", "1")
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "ops:read")
    import json, tempfile, pathlib, importlib
    d = tempfile.mkdtemp()
    idx = pathlib.Path(d) / "index.json"
    idx.write_text(json.dumps({"items": [], "generated_at": 0}), encoding="utf-8")
    monkeypatch.setenv("DECISIONOS_EVIDENCE_INDEX", str(idx))

    import apps.ops.api.cards_delta as cards_delta
    importlib.reload(cards_delta)

    test_app = FastAPI()
    test_app.include_router(cards_delta.router)
    c = TestClient(test_app)
    r1 = c.get("/ops/cards/reason-trends", headers={"x-decisionos-scopes": "*"})
    assert r1.status_code == 200
    r2 = c.get("/ops/cards/reason-trends", headers={"x-decisionos-scopes": "*"})
    assert r2.status_code == 200
    assert "delta" in r2.json()
