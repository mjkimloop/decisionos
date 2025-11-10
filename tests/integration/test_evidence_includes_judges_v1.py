import json

import pytest

pytestmark = [pytest.mark.gate_aj]

from apps.obs.evidence.snapshot import build_snapshot
from apps.rating.engine import RatingResult


def test_evidence_includes_judges_block():
    rating = RatingResult(subtotal=0.0, items=[])
    judges = {
        "k": 2,
        "n": 3,
        "final": "pass",
        "votes": [{"id": "local-a", "decision": "pass", "latency_ms": 12, "reasons": [], "version": "v"}],
    }

    snap = build_snapshot(
        version="v0.5.11i",
        tenant="tenant-x",
        witness_csv_path="w.csv",
        witness_rows=1,
        witness_csv_sha256="abc",
        buckets={},
        deltas_by_metric={},
        rating=rating,
        quota=[],
        budget_level="ok",
        budget_spent=0.0,
        budget_limit=1.0,
        anomaly_is_spike=False,
        anomaly_ewma=0.0,
        anomaly_ratio=0.0,
        judges=judges,
    )

    data = json.loads(snap.to_json())
    assert data["judges"]["final"] == "pass"
    assert len(data["judges"]["votes"]) == 1
