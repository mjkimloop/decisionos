import json
import os

from apps.ops.api.cards_data import compute_reason_trends


def test_weights_and_buckets_basic(tmp_path, monkeypatch):
    idx = tmp_path / "index.json"
    idx.write_text(
        json.dumps(
            {
                "generated_at": "2025-11-18T01:23:45Z",
                "buckets": [
                    {"ts": "2025-11-18T01:00:00Z", "reasons": {"perf": 3, "infra-latency": 2}},
                    {"ts": "2025-11-18T02:00:00Z", "reasons": {"perf": 1, "infra-latency": 5}},
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("DECISIONOS_EVIDENCE_INDEX", str(idx))

    weights = {
        "groups": {"perf": {"weight": 1.0}, "infra": {"weight": 1.5}},
        "labels": {"perf": {"weight": 1.0}, "infra-latency": {"weight": 1.0}, "infra-error": {"weight": 2.0}},
        "group_map": {"perf": ["perf"], "infra": ["infra-latency", "infra-error"]},
    }
    result = compute_reason_trends(index_path=str(idx), weights=weights, bucket="hour")
    assert result["groups"]["infra"]["score"] > result["groups"]["perf"]["score"]
    assert len(result["buckets"]) == 2
