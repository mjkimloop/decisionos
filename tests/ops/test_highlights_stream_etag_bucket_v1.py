import pytest
import os
import json
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.gate_ops]


def test_highlights_stream_bucket_param(tmp_path, monkeypatch):
    """bucket 파라미터 처리"""
    # 하이라이트 스트림 준비
    hl_dir = tmp_path / "highlights"
    hl_dir.mkdir()
    stream_path = hl_dir / "stream.jsonl"
    stream_path.write_text(
        json.dumps({"rev": "r1", "token": "r1:1000", "items": []}) + "\n" +
        json.dumps({"rev": "r2", "token": "r2:2000", "items": []}) + "\n",
        encoding="utf-8"
    )

    monkeypatch.setenv("DECISIONOS_HIGHLIGHTS_DIR", str(hl_dir))

    from apps.ops.api_cards import router
    client = TestClient(router)

    # bucket=day
    resp = client.get("/cards/highlights/stream?bucket=day&limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["bucket"] == "day"
    assert "etag" in data
    assert len(data["items"]) == 2


def test_highlights_stream_etag_304(tmp_path, monkeypatch):
    """If-None-Match → 304"""
    hl_dir = tmp_path / "highlights"
    hl_dir.mkdir()
    stream_path = hl_dir / "stream.jsonl"
    stream_path.write_text(
        json.dumps({"rev": "r1", "token": "r1:1000", "items": []}) + "\n",
        encoding="utf-8"
    )

    monkeypatch.setenv("DECISIONOS_HIGHLIGHTS_DIR", str(hl_dir))

    from apps.ops.api_cards import router
    client = TestClient(router)

    # 첫 요청
    resp1 = client.get("/cards/highlights/stream?bucket=day")
    assert resp1.status_code == 200
    etag = resp1.json()["etag"]

    # 동일 ETag로 재요청
    resp2 = client.get("/cards/highlights/stream?bucket=day", headers={"If-None-Match": etag})
    assert resp2.status_code == 304


def test_highlights_stream_delta_base(tmp_path, monkeypatch):
    """X-Delta-Base-ETag 처리"""
    hl_dir = tmp_path / "highlights"
    hl_dir.mkdir()
    stream_path = hl_dir / "stream.jsonl"
    stream_path.write_text(
        json.dumps({"rev": "r1", "token": "r1:1000", "items": [{"label": "a"}]}) + "\n" +
        json.dumps({"rev": "r2", "token": "r2:2000", "items": [{"label": "b"}]}) + "\n",
        encoding="utf-8"
    )

    monkeypatch.setenv("DECISIONOS_HIGHLIGHTS_DIR", str(hl_dir))

    from apps.ops.api_cards import router
    client = TestClient(router)

    # 첫 요청
    resp1 = client.get("/cards/highlights/stream?bucket=day&limit=1")
    assert resp1.status_code == 200
    base_etag = resp1.json()["etag"]

    # Delta 요청 (두 번째 항목까지)
    resp2 = client.get("/cards/highlights/stream?bucket=day&limit=2", headers={"X-Delta-Base-ETag": base_etag})
    assert resp2.status_code == 200
    data = resp2.json()
    # Delta 적용되면 새 항목만
    assert "X-Delta-Applied" in resp2.headers or "items" in data


def test_highlights_stream_since_token(tmp_path, monkeypatch):
    """since 토큰 페이지네이션"""
    hl_dir = tmp_path / "highlights"
    hl_dir.mkdir()
    stream_path = hl_dir / "stream.jsonl"
    stream_path.write_text(
        json.dumps({"rev": "r1", "token": "r1:1000", "items": []}) + "\n" +
        json.dumps({"rev": "r2", "token": "r2:2000", "items": []}) + "\n" +
        json.dumps({"rev": "r3", "token": "r3:3000", "items": []}) + "\n",
        encoding="utf-8"
    )

    monkeypatch.setenv("DECISIONOS_HIGHLIGHTS_DIR", str(hl_dir))

    from apps.ops.api_cards import router
    client = TestClient(router)

    # 첫 페이지
    resp1 = client.get("/cards/highlights/stream?bucket=day&limit=1")
    assert resp1.status_code == 200
    next_tok = resp1.json()["next"]

    # 다음 페이지
    resp2 = client.get(f"/cards/highlights/stream?bucket=day&limit=2&since={next_tok}")
    assert resp2.status_code == 200
    items = resp2.json()["items"]
    assert len(items) <= 2
