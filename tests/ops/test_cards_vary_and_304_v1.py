from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
import os


def test_cards_vary_and_304_headers(tmp_path):
    """Test that cards delta endpoint returns correct headers for caching"""
    # Create evidence index
    idx = tmp_path / "index.json"
    idx.write_text('{"generated_at":1234567890,"reason_trends":[["perf",3]],"top_impact":["perf"]}', encoding="utf-8")

    os.environ["DECISIONOS_EVIDENCE_INDEX"] = str(idx)
    os.environ["DECISIONOS_RBAC_TEST_MODE"] = "1"

    from apps.ops.api import cards_delta

    cards_delta.INDEX_PATH = str(idx)

    app = FastAPI()
    app.include_router(cards_delta.router, prefix="/ops/cards")
    c = TestClient(app)

    # First request
    r1 = c.get("/ops/cards/reason-trends?period=7d", headers={"X-Scopes": "ops:read"})
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    assert etag
    assert "Vary" in r1.headers
    assert "Authorization" in r1.headers["Vary"]
    assert "Cache-Control" in r1.headers
    assert "Last-Modified" in r1.headers

    # Second request with If-None-Match should return 304
    r2 = c.get("/ops/cards/reason-trends?period=7d", headers={"If-None-Match": etag, "X-Scopes": "ops:read"})
    assert r2.status_code == 304
    assert r2.headers.get("ETag") == etag
    assert r2.headers.get("Content-Length") == "0"
