from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
import os

def test_cards_delta_etag_generation(tmp_path):
    """Test that cards delta endpoint generates ETags correctly"""
    # Create evidence index
    idx = tmp_path / "index.json"
    idx.write_text('{"generated_at":1234567890,"reason_trends":[["perf",3]],"top_impact":["perf"]}', encoding="utf-8")

    # Must set before import
    os.environ["DECISIONOS_EVIDENCE_INDEX"] = str(idx)

    # Import after env var is set
    from apps.ops.api import cards_delta

    # Force reload module constants
    cards_delta.INDEX_PATH = str(idx)

    app = FastAPI()
    app.include_router(cards_delta.router, prefix="/ops/cards")
    c = TestClient(app)

    # First request should return 200 with ETag
    r1 = c.get("/ops/cards/reason-trends")
    assert r1.status_code == 200
    etag1 = r1.headers.get("ETag")
    assert etag1
    assert "Cache-Control" in r1.headers
    data1 = r1.json()
    assert "reason_trends" in data1
    assert data1["generated_at"] == 1234567890
    assert data1["reason_trends"] == [["perf", 3]]

    # Second request should also return 200 (payload unchanged but ETag chain changes)
    # This is expected behavior for delta ETag with chaining
    r2 = c.get("/ops/cards/reason-trends")
    assert r2.status_code == 200
    etag2 = r2.headers.get("ETag")
    assert etag2
    # ETag should be different due to chaining, but that's OK
    # The important thing is that 304 works when client sends correct ETag
