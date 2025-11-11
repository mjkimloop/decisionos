import pytest
import os
import json
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.gate_ops]


@pytest.fixture
def mock_environment(tmp_path, monkeypatch):
    """환경 설정: 인덱스, 카탈로그, 임계값"""
    idx = {
        "rows": [
            {"group": "infra", "label": "reason:infra-latency", "count": 6},
            {"group": "perf", "label": "reason:perf", "count": 2}
        ],
        "rev": "42"
    }
    p_idx = tmp_path / "summary.json"
    p_idx.write_text(json.dumps(idx), encoding="utf-8")
    monkeypatch.setenv("DECISIONOS_EVIDENCE_INDEX", str(p_idx))

    cat = {
        "groups": {
            "infra": {"weight": 1.3, "color": "c0392b"},
            "perf": {"weight": 1.1, "color": "2980b9"}
        },
        "labels": [
            {"name": "reason:infra-latency", "group": "infra"},
            {"name": "reason:perf", "group": "perf"}
        ]
    }
    p_cat = tmp_path / "catalog.json"
    p_cat.write_text(json.dumps(cat), encoding="utf-8")
    monkeypatch.setenv("LABEL_CATALOG_PATH", str(p_cat))

    thr = {
        "default": {"warn": 5, "crit": 10},
        "labels": {
            "reason:infra-latency": {"warn": 3, "crit": 7}
        }
    }
    p_thr = tmp_path / "thresholds.json"
    p_thr.write_text(json.dumps(thr), encoding="utf-8")
    monkeypatch.setenv("THRESHOLDS_PATH", str(p_thr))

    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "ops:read")


def test_overlay_none(mock_environment):
    """overlay=none: 기본 매트릭스만"""
    from apps.ops.api_cards import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)
    r = client.get("/cards/label-heatmap?period=7d&bucket=day&overlay=none")
    assert r.status_code == 200
    data = r.json()
    assert data["overlays"] is None


def test_overlay_threshold(mock_environment):
    """overlay=threshold: 임계값 상태 표시"""
    from apps.ops.api_cards import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)
    r = client.get("/cards/label-heatmap?period=7d&bucket=day&overlay=threshold")
    assert r.status_code == 200
    data = r.json()
    assert "threshold" in data["overlays"]
    # infra-latency count=6 → warn 임계(3) 초과
    assert data["overlays"]["threshold"]["infra"]["reason:infra-latency"] in ("warn", "crit")


def test_overlay_weighted(mock_environment):
    """overlay=weighted: 가중 점수"""
    from apps.ops.api_cards import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)
    r = client.get("/cards/label-heatmap?period=7d&bucket=day&overlay=weighted")
    assert r.status_code == 200
    data = r.json()
    assert "weighted" in data["overlays"]
    # infra weight=1.3, count=6 → weighted=7.8
    assert data["overlays"]["weighted"]["infra"]["reason:infra-latency"] == pytest.approx(7.8, rel=0.01)


def test_overlay_both(mock_environment):
    """overlay=both: threshold + weighted 동시"""
    from apps.ops.api_cards import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)
    r = client.get("/cards/label-heatmap?period=7d&bucket=day&overlay=both")
    assert r.status_code == 200
    data = r.json()
    assert "threshold" in data["overlays"]
    assert "weighted" in data["overlays"]


def test_overlay_etag_variation(mock_environment):
    """overlay 변경 시 ETag 달라짐"""
    from apps.ops.api_cards import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)
    r1 = client.get("/cards/label-heatmap?period=7d&bucket=day&overlay=none")
    r2 = client.get("/cards/label-heatmap?period=7d&bucket=day&overlay=threshold")

    assert r1.status_code == 200
    assert r2.status_code == 200
    etag1 = r1.json()["etag"]
    etag2 = r2.json()["etag"]
    assert etag1 != etag2


def test_overlay_304_same_request(mock_environment):
    """동일 요청 시 304"""
    from apps.ops.api_cards import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)
    r1 = client.get("/cards/label-heatmap?period=7d&bucket=day&overlay=weighted")
    assert r1.status_code == 200
    etag = r1.json()["etag"]

    r2 = client.get("/cards/label-heatmap?period=7d&bucket=day&overlay=weighted", headers={"If-None-Match": etag})
    assert r2.status_code == 304


def test_invalid_overlay(mock_environment):
    """잘못된 overlay 파라미터 → 400"""
    from apps.ops.api_cards import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)
    r = client.get("/cards/label-heatmap?period=7d&bucket=day&overlay=invalid")
    assert r.status_code == 400
