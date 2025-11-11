import pytest
import os
import json
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.gate_ops]


def test_explain_adds_metadata(tmp_path, monkeypatch):
    """explain=1이면 가중치 및 사유코드 추가"""
    # 하이라이트 스트림 준비
    hl_dir = tmp_path / "highlights"
    hl_dir.mkdir()
    stream_path = hl_dir / "stream.jsonl"
    stream_path.write_text(
        json.dumps({"rev": "r1", "token": "r1:1000", "items": [
            {"group": "infra", "label": "reason:infra-latency", "value": 1}
        ]}) + "\n",
        encoding="utf-8"
    )

    # 카탈로그 준비
    cat_path = tmp_path / "catalog.json"
    cat_path.write_text(json.dumps({
        "groups": {
            "infra": {"weight": 1.3, "color": "c0392b"},
            "perf": {"weight": 1.5, "color": "e67e22"}
        },
        "labels": [
            {"name": "reason:infra-latency"},
            {"name": "reason:perf"}
        ]
    }), encoding="utf-8")

    monkeypatch.setenv("DECISIONOS_HIGHLIGHTS_DIR", str(hl_dir))
    monkeypatch.setenv("LABEL_CATALOG_PATH", str(cat_path))

    from apps.ops.api_cards import router
    client = TestClient(router)

    # explain=1 요청
    resp = client.get("/cards/highlights/stream?bucket=day&explain=1&limit=1")
    assert resp.status_code == 200
    data = resp.json()

    # explain 필드 확인
    assert "items" in data
    assert len(data["items"]) > 0
    item = data["items"][0]["items"][0]
    assert "explain" in item
    assert item["explain"]["weight"] == 1.3
    assert "reason:infra-latency" in item["explain"]["reason_codes"]


def test_explain_changes_etag(tmp_path, monkeypatch):
    """explain 값에 따라 ETag가 달라짐"""
    hl_dir = tmp_path / "highlights"
    hl_dir.mkdir()
    stream_path = hl_dir / "stream.jsonl"
    stream_path.write_text(
        json.dumps({"rev": "r1", "token": "r1:1000", "items": [
            {"group": "infra", "label": "reason:infra-latency", "value": 1}
        ]}) + "\n",
        encoding="utf-8"
    )

    cat_path = tmp_path / "catalog.json"
    cat_path.write_text(json.dumps({
        "groups": {"infra": {"weight": 1.3}},
        "labels": [{"name": "reason:infra-latency"}]
    }), encoding="utf-8")

    monkeypatch.setenv("DECISIONOS_HIGHLIGHTS_DIR", str(hl_dir))
    monkeypatch.setenv("LABEL_CATALOG_PATH", str(cat_path))

    from apps.ops.api_cards import router
    client = TestClient(router)

    # explain=0
    resp0 = client.get("/cards/highlights/stream?bucket=day&explain=0&limit=1")
    etag0 = resp0.headers.get("ETag")

    # explain=1
    resp1 = client.get("/cards/highlights/stream?bucket=day&explain=1&limit=1")
    etag1 = resp1.headers.get("ETag")

    # ETag가 달라야 함
    assert etag0 != etag1


def test_explain_304_with_same_etag(tmp_path, monkeypatch):
    """explain 포함 ETag로 304 처리"""
    hl_dir = tmp_path / "highlights"
    hl_dir.mkdir()
    stream_path = hl_dir / "stream.jsonl"
    stream_path.write_text(
        json.dumps({"rev": "r1", "token": "r1:1000", "items": [
            {"group": "infra", "label": "reason:infra-latency", "value": 1}
        ]}) + "\n",
        encoding="utf-8"
    )

    cat_path = tmp_path / "catalog.json"
    cat_path.write_text(json.dumps({
        "groups": {"infra": {"weight": 1.3}},
        "labels": [{"name": "reason:infra-latency"}]
    }), encoding="utf-8")

    monkeypatch.setenv("DECISIONOS_HIGHLIGHTS_DIR", str(hl_dir))
    monkeypatch.setenv("LABEL_CATALOG_PATH", str(cat_path))

    from apps.ops.api_cards import router
    client = TestClient(router)

    # 첫 요청
    resp1 = client.get("/cards/highlights/stream?bucket=day&explain=1&limit=1")
    assert resp1.status_code == 200
    etag = resp1.headers.get("ETag")

    # 동일 ETag로 재요청
    resp2 = client.get("/cards/highlights/stream?bucket=day&explain=1&limit=1", headers={"If-None-Match": etag})
    assert resp2.status_code == 304


def test_explain_without_catalog(tmp_path, monkeypatch):
    """카탈로그 없어도 에러 없이 기본 가중치 1.0"""
    hl_dir = tmp_path / "highlights"
    hl_dir.mkdir()
    stream_path = hl_dir / "stream.jsonl"
    stream_path.write_text(
        json.dumps({"rev": "r1", "token": "r1:1000", "items": [
            {"group": "infra", "label": "reason:infra-latency", "value": 1}
        ]}) + "\n",
        encoding="utf-8"
    )

    monkeypatch.setenv("DECISIONOS_HIGHLIGHTS_DIR", str(hl_dir))
    monkeypatch.setenv("LABEL_CATALOG_PATH", str(tmp_path / "nonexistent.json"))

    from apps.ops.api_cards import router
    client = TestClient(router)

    resp = client.get("/cards/highlights/stream?bucket=day&explain=1&limit=1")
    assert resp.status_code == 200
    data = resp.json()

    # 기본 가중치 1.0
    item = data["items"][0]["items"][0]
    assert item["explain"]["weight"] == 1.0
