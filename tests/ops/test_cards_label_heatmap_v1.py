import pytest
import os
import json
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.gate_ops]


@pytest.fixture
def mock_index_and_catalog(tmp_path, monkeypatch):
    """최소 인덱스/카탈로그 준비"""
    idx = {
        "rows": [
            {"group": "infra", "label": "reason:infra-latency", "count": 2},
            {"group": "perf", "label": "reason:perf", "count": 1}
        ],
        "rev": "1"
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

    # RBAC
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "ops:read")


def test_label_heatmap_200(mock_index_and_catalog):
    """라벨 히트맵 API 200 응답 확인"""
    from apps.ops.api_cards import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)
    r = client.get("/cards/label-heatmap?period=7d&bucket=day")
    assert r.status_code == 200
    data = r.json()
    assert "period" in data
    assert "groups" in data
    assert "labels" in data
    assert "matrix" in data
    assert "etag" in data
    assert data["period"] == "7d"
    assert "infra" in data["groups"]
    assert "perf" in data["groups"]


def test_label_heatmap_etag_304(mock_index_and_catalog):
    """ETag 기반 304 응답 확인"""
    from apps.ops.api_cards import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)
    r1 = client.get("/cards/label-heatmap?period=7d&bucket=day")
    assert r1.status_code == 200
    etag = r1.json()["etag"]

    # 같은 ETag로 재요청
    r2 = client.get("/cards/label-heatmap?period=7d&bucket=day", headers={"If-None-Match": etag})
    assert r2.status_code == 304


def test_label_heatmap_missing_index(tmp_path, monkeypatch):
    """인덱스 파일 없을 때 503"""
    monkeypatch.setenv("DECISIONOS_EVIDENCE_INDEX", str(tmp_path / "nonexistent.json"))
    monkeypatch.setenv("LABEL_CATALOG_PATH", str(tmp_path / "nonexistent_cat.json"))
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "ops:read")

    from apps.ops.api_cards import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)
    r = client.get("/cards/label-heatmap?period=7d")
    assert r.status_code == 503


def test_label_heatmap_matrix_content(mock_index_and_catalog):
    """매트릭스 내용 확인"""
    from apps.ops.api_cards import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)
    r = client.get("/cards/label-heatmap?period=7d&bucket=day")
    assert r.status_code == 200
    data = r.json()
    matrix = data["matrix"]
    # infra 그룹의 reason:infra-latency 카운트 확인
    assert "infra" in matrix
    assert "reason:infra-latency" in matrix["infra"]
    assert matrix["infra"]["reason:infra-latency"] == 2
