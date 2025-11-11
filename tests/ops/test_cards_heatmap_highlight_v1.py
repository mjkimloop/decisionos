import pytest
import os
import json
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.gate_ops]


@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    """최소 환경 설정"""
    os.environ["DECISIONOS_ALLOW_SCOPES"] = "ops:read"
    idx = {
        "rows": [
            {"group": "infra", "label": "reason:infra-latency", "count": 5},
            {"group": "perf", "label": "reason:perf", "count": 10},
            {"group": "canary", "label": "reason:canary", "count": 2}
        ],
        "rev": "99"
    }
    (tmp_path / "summary.json").write_text(json.dumps(idx), encoding="utf-8")
    os.environ["DECISIONOS_EVIDENCE_INDEX"] = str(tmp_path / "summary.json")


def test_highlight_top_weighted(mock_env):
    """상위 가중 하이라이트"""
    from apps.ops.api_cards import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)

    c = TestClient(app)
    r = c.get("/cards/label-heatmap?period=7d&highlight=2&mode=weighted")
    assert r.status_code == 200
    j = r.json()
    assert "highlights" in j and len(j["highlights"]) <= 2
    vals = [h["value"] for h in j["highlights"]]
    assert vals == sorted(vals, reverse=True)
    # rank 확인
    for i, h in enumerate(j["highlights"], 1):
        assert h["rank"] == i


def test_highlight_zero_disabled(mock_env):
    """highlight=0 시 비활성화"""
    from apps.ops.api_cards import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)

    c = TestClient(app)
    r = c.get("/cards/label-heatmap?period=7d&highlight=0")
    assert r.status_code == 200
    j = r.json()
    assert j["highlights"] is None


def test_highlight_mode_raw(mock_env):
    """mode=raw 사용"""
    from apps.ops.api_cards import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)

    c = TestClient(app)
    r = c.get("/cards/label-heatmap?period=7d&highlight=3&mode=raw")
    assert r.status_code == 200
    j = r.json()
    assert "highlights" in j
    # raw mode는 가중치 적용 안 함 (count 그대로)
    for h in j["highlights"]:
        assert "value" in h and h["value"] > 0


def test_highlight_etag_changes(mock_env):
    """highlight 파라미터 변경 시 ETag 달라짐"""
    from apps.ops.api_cards import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)

    c = TestClient(app)
    r1 = c.get("/cards/label-heatmap?period=7d&highlight=0")
    r2 = c.get("/cards/label-heatmap?period=7d&highlight=5")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["etag"] != r2.json()["etag"]
