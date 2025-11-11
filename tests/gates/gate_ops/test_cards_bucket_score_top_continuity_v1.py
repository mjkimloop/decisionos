import pytest
import os, json
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

def _row(ts, reason):
    return json.dumps({"ts": ts, "reason": reason})

@pytest.mark.gate_ops
def test_weighted_scores_and_top_buckets(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from apps.ops.api_cards import router

    app = FastAPI()
    app.include_router(router, prefix="/ops")

    # 데이터: hour=10(infra 2건), hour=11(perf 3건)
    p = tmp_path/"reasons.jsonl"
    s = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    p.write_text("\n".join([
        _row((s+timedelta(minutes=1)).isoformat(),  "reason:infra-latency"),
        _row((s+timedelta(minutes=2)).isoformat(),  "reason:infra-error"),
        _row((s+timedelta(hours=1, minutes=1)).isoformat(), "reason:perf"),
        _row((s+timedelta(hours=1, minutes=2)).isoformat(), "reason:perf"),
        _row((s+timedelta(hours=1, minutes=3)).isoformat(), "reason:perf"),
    ]), encoding="utf-8")
    monkeypatch.setenv("REASON_EVENTS_PATH", str(p))
    # 가중치 명시: infra=3, perf=2
    monkeypatch.setenv("REASON_GROUP_WEIGHTS", json.dumps({"infra":3,"perf":2}))
    client = TestClient(app)
    q = {
        "start": s.isoformat(),
        "end":   (s+timedelta(hours=2)).isoformat(),
        "top": 5, "bucket": "hour", "bucket_limit": 10, "top_buckets": 2
    }
    r = client.get("/ops/cards/reason-trends/summary", params=q)
    assert r.status_code == 200
    j = r.json()
    b = j.get("buckets")
    assert b is not None
    assert len(b) >= 2
    # hour=10: infra 2건 → score=2*3=6
    # hour=11: perf 3건 → score=3*2=6 (동점 허용)
    scores = [bkt["score"] for bkt in b]
    assert all(abs(x-6.0) < 1e-6 for x in scores)
    assert isinstance(j["top_buckets"], list) and len(j["top_buckets"]) == 2

@pytest.mark.gate_ops
def test_continuity_pagination_no_overlap(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from apps.ops.api_cards import router

    app = FastAPI()
    app.include_router(router, prefix="/ops")

    p = tmp_path/"reasons.jsonl"
    s = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    # 10시/11시/12시… 3개 버킷
    lines = []
    for h in range(3):
        lines.append(_row((s+timedelta(hours=h, minutes=1)).isoformat(),  "reason:perf"))
    p.write_text("\n".join(lines), encoding="utf-8")
    monkeypatch.setenv("REASON_EVENTS_PATH", str(p))

    client = TestClient(app)
    base = {"top":5, "bucket":"hour", "bucket_limit":1}
    q1 = {"start": s.isoformat(), "end": (s+timedelta(hours=4)).isoformat(), **base}
    r1 = client.get("/ops/cards/reason-trends/summary", params=q1)
    assert r1.status_code == 200
    j1 = r1.json()
    b1 = j1["buckets"]
    assert len(b1) == 1
    tok = r1.headers.get("X-Bucket-Continuity-Token")
    assert tok

    # 다음 페이지
    r2 = client.get("/ops/cards/reason-trends/summary", params=q1, headers={"X-Bucket-Continuity-Token": tok})
    j2 = r2.json()
    b2 = j2["buckets"]
    assert len(b2) == 1
    # 겹치지 않음
    assert b1[0]["end"] < b2[0]["end"]
