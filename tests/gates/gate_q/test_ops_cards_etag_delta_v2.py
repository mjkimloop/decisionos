import time
from starlette.testclient import TestClient

from apps.ops.api.server import app


def test_cards_etag_and_304_and_delta(monkeypatch):
    monkeypatch.setenv("DECISIONOS_RBAC_TEST_MODE", "1")

    c = TestClient(app)

    r1 = c.get("/ops/cards/reason-trends", headers={"X-Scopes": "ops:read"})
    assert r1.status_code == 200
    etag1 = r1.headers.get("ETag")
    assert etag1

    r2 = c.get("/ops/cards/reason-trends", headers={"X-Scopes": "ops:read", "If-None-Match": etag1})
    assert r2.status_code == 304

    time.sleep(1)
    r3 = c.get("/ops/cards/reason-trends", headers={"X-Scopes": "ops:read", "X-Delta-Base-ETag": etag1})
    assert r3.status_code == 200
    js = r3.json()
    assert js.get("delta") is True
    assert r3.headers.get("X-Delta-Mode") == "1"
