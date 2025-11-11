"""
Test Reason Summary Rules v1
규칙 기반 reason 요약 테스트
"""
import pytest
import json
import os
from apps.ops.explain.summary import summarize_reasons


def test_top_n_labels():
    """Top-N 라벨 추출"""
    items = [
        {"label": "label_a", "group": "infra", "value": 10},
        {"label": "label_b", "group": "app", "value": 8},
        {"label": "label_c", "group": "data", "value": 6},
        {"label": "label_d", "group": "infra", "value": 4},
        {"label": "label_e", "group": "app", "value": 2},
        {"label": "label_f", "group": "data", "value": 1},
    ]

    summary = summarize_reasons(items, top_n=3, compress_threshold=3)

    # Top-3 라벨: label_a(10), label_b(8), label_c(6)
    assert len(summary["top_labels"]) == 4  # Top-3 + [+others]
    assert summary["top_labels"][0]["label"] == "label_a"
    assert summary["top_labels"][0]["count"] == 10
    assert summary["top_labels"][1]["label"] == "label_b"
    assert summary["top_labels"][1]["count"] == 8
    assert summary["top_labels"][2]["label"] == "label_c"
    assert summary["top_labels"][2]["count"] == 6

    # 나머지: label_d(4) + label_e(2) + label_f(1) = 7
    assert summary["top_labels"][3]["label"] == "[+others]"
    assert summary["top_labels"][3]["count"] == 7

    # Top-3 그룹: infra(14), app(10), data(7)
    assert len(summary["top_groups"]) == 3  # 전체 3개뿐이므로 [+others] 없음
    assert summary["top_groups"][0]["group"] == "infra"
    assert summary["top_groups"][0]["count"] == 14


def test_compress_others():
    """나머지 압축([+others])"""
    items = [
        {"label": "label_a", "group": "infra", "value": 100},
        {"label": "label_b", "group": "app", "value": 90},
        {"label": "label_c", "group": "data", "value": 1},
        {"label": "label_d", "group": "infra", "value": 1},
    ]

    summary = summarize_reasons(items, top_n=2, compress_threshold=3)

    # Top-2: label_a(100), label_b(90)
    # 나머지: label_c(1) + label_d(1) = 2 < compress_threshold=3
    # [+others] 추가되지 않음
    assert len(summary["top_labels"]) == 2
    assert summary["top_labels"][0]["label"] == "label_a"
    assert summary["top_labels"][1]["label"] == "label_b"

    # compress_threshold=1로 설정하면 [+others] 추가됨
    summary2 = summarize_reasons(items, top_n=2, compress_threshold=1)
    assert len(summary2["top_labels"]) == 3
    assert summary2["top_labels"][2]["label"] == "[+others]"
    assert summary2["top_labels"][2]["count"] == 2


def test_summary_api(tmp_path, monkeypatch):
    """API 엔드포인트 응답 검증"""
    from fastapi.testclient import TestClient

    # Mock highlights stream
    hl_dir = tmp_path / "highlights"
    hl_dir.mkdir()
    stream_path = hl_dir / "stream.jsonl"

    stream_data = [
        {"items": [
            {"label": "reason:infra-latency", "group": "infra", "value": 5},
            {"label": "reason:app-error", "group": "app", "value": 3},
        ]},
        {"items": [
            {"label": "reason:infra-latency", "group": "infra", "value": 2},
            {"label": "reason:data-loss", "group": "data", "value": 1},
        ]},
    ]
    stream_path.write_text("\n".join(json.dumps(r) for r in stream_data))

    monkeypatch.setenv("DECISIONOS_HIGHLIGHTS_DIR", str(hl_dir))

    # Import app
    from apps.ops.api_cards import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    # Request
    resp = client.get("/cards/reason-summary?bucket=day&top_n=2&compress_threshold=3")
    assert resp.status_code == 200

    data = resp.json()
    assert "top_labels" in data
    assert "top_groups" in data
    assert data["total_items"] == 4
    assert data["unique_labels"] == 3
    assert data["unique_groups"] == 3

    # Top-2 labels: reason:infra-latency(7), reason:app-error(3)
    assert len(data["top_labels"]) == 2  # compress_threshold=3이므로 나머지(1) < 3
    assert data["top_labels"][0]["label"] == "reason:infra-latency"
    assert data["top_labels"][0]["count"] == 7
    assert data["top_labels"][1]["label"] == "reason:app-error"
    assert data["top_labels"][1]["count"] == 3

    # Top-2 groups: infra(7), app(3)
    assert len(data["top_groups"]) == 2
    assert data["top_groups"][0]["group"] == "infra"
    assert data["top_groups"][0]["count"] == 7
