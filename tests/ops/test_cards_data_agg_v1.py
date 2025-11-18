import json
from apps.ops.api.cards_data import compute_reason_trends


def test_cards_agg_smoke(tmp_path):
    idx = {
        "generated_at": "2025-11-18T06:00:00Z",
        "items": [
            {"ts": "2025-11-18T05:00:00Z", "reason": "infra-latency", "group": "infra", "weight": 1.0},
            {"ts": "2025-11-18T04:30:00Z", "reason": "perf", "group": "perf", "weight": 0.5},
        ],
    }
    p = tmp_path / "index.json"
    p.write_text(json.dumps(idx), encoding="utf-8")
    out = compute_reason_trends(period="1d", bucket="hour", index_path=str(p))
    assert out["summary"]["total_events"] == 2
    assert len(out["top_reasons"]) >= 1
