import pytest
import os, json, tempfile
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

def _w(ts, reason):
    return json.dumps({"ts": ts, "reason": reason})

@pytest.mark.gate_ops
def test_window_filter_and_304(monkeypatch, tmp_path):
    # Create a minimal FastAPI app for testing
    from fastapi import FastAPI
    from apps.ops.api_cards import router

    app = FastAPI()
    app.include_router(router, prefix="/ops")

    p = tmp_path/"reasons.jsonl"
    s = datetime(2025,1,1,10,0,0,tzinfo=timezone.utc)
    data = "\n".join([
        _w((s+timedelta(minutes=1)).isoformat(), "reason:infra-latency"),
        _w((s+timedelta(minutes=2)).isoformat(), "reason:perf"),
    ])
    p.write_text(data, encoding="utf-8")
    monkeypatch.setenv("REASON_EVENTS_PATH", str(p))

    client = TestClient(app)
    q = {"start": s.isoformat(), "end": (s+timedelta(hours=1)).isoformat(), "top": 5}
    r1 = client.get("/ops/cards/reason-trends/summary", params=q)
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    assert etag is not None

    r2 = client.get("/ops/cards/reason-trends/summary", params=q,
                    headers={"If-None-Match": etag})
    assert r2.status_code == 304

@pytest.mark.gate_ops
def test_delta_token_added_changed(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from apps.ops.api_cards import router

    app = FastAPI()
    app.include_router(router, prefix="/ops")

    p = tmp_path/"reasons.jsonl"
    s = datetime(2025,1,1,10,0,0,tzinfo=timezone.utc)
    # 초기 2건
    p.write_text("\n".join([
        _w((s+timedelta(minutes=1)).isoformat(), "reason:infra-latency"),
        _w((s+timedelta(minutes=2)).isoformat(), "reason:perf"),
    ]), encoding="utf-8")
    monkeypatch.setenv("REASON_EVENTS_PATH", str(p))
    client = TestClient(app)
    q = {"start": s.isoformat(), "end": (s+timedelta(hours=1)).isoformat(), "top": 5}
    r1 = client.get("/ops/cards/reason-trends/summary", params=q)
    j1 = r1.json()
    t1 = j1["delta_token"]
    assert t1 is not None
    # First snapshot: reason:infra-latency=1, reason:perf=1
    assert j1["raw"]["reason:infra-latency"] == 1
    assert j1["raw"]["reason:perf"] == 1

    # 이벤트 추가(변화 발생)
    with open(p, "a", encoding="utf-8") as f:
        f.write("\n"+_w((s+timedelta(minutes=3)).isoformat(), "reason:infra-latency"))

    r2 = client.get("/ops/cards/reason-trends/summary", params=q,
                    headers={"X-If-Delta-Token": t1})
    j = r2.json()
    # Now reason:infra-latency=2, reason:perf=1
    assert j["raw"]["reason:infra-latency"] == 2
    assert j["delta"] is not None
    # infra-latency 카운트가 증가 → changed
    d = j["delta"]
    changed = d.get("changed", {})
    assert "reason:infra-latency" in changed
    assert changed["reason:infra-latency"]["from"] == 1
    assert changed["reason:infra-latency"]["to"] == 2
    assert changed["reason:infra-latency"]["delta"] == 1
