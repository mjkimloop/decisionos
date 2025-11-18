import json
from pathlib import Path

from starlette.testclient import TestClient

from apps.ops.api.server import app


def test_cards_reads_index_and_catalog(tmp_path, monkeypatch):
    idx = {
        "items": [
            {"labels": ["reason:infra-latency", "reason:perf"]},
            {"reasons": [{"code": "reason:perf"}, {"code": "reason:quota"}]},
        ]
    }
    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps(idx), encoding="utf-8")

    cat = {
        "groups": {
            "infra": {"weight": 1.7},
            "perf": {"weight": 2.2},
            "quota": {"weight": 1.0},
            "other": {"weight": 1.0},
        },
        "labels": {
            "reason:infra-latency": {"group": "infra"},
            "reason:perf": {"group": "perf"},
            "reason:quota": {"group": "quota"},
        },
    }
    cat_path = tmp_path / "catalog.json"
    cat_path.write_text(json.dumps(cat), encoding="utf-8")

    monkeypatch.setenv("DECISIONOS_EVIDENCE_INDEX", str(index_path))
    monkeypatch.setenv("DECISIONOS_LABEL_CATALOG", str(cat_path))
    monkeypatch.setenv("DECISIONOS_RBAC_TEST_MODE", "1")

    c = TestClient(app)
    r = c.get("/ops/cards/reason-trends", headers={"X-Scopes": "ops:read"})
    assert r.status_code == 200
    body = r.json()
    assert body["groups"]["perf"]["count"] == 2
    assert body["groups"]["infra"]["count"] == 1
    assert body["groups"]["quota"]["count"] == 1
    assert body["top"][0]["group"] == "perf"
