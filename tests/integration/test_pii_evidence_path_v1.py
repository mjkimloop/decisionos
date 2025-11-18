import os
import pytest
from apps.obs.evidence.snapshot import build_snapshot
from apps.limits.quota import QuotaDecision

pytestmark = pytest.mark.integration

def test_evidence_snapshot_with_pii(monkeypatch):
    monkeypatch.setenv("DECISIONOS_PII_ENABLE", "1")
    class DummyRatingItem:
        def __init__(self):
            self.metric = "perf"
            self.amount = 1.0
            self.included = True
            self.overage_units = 0.0

    class DummyRating:
        subtotal = 1.0
        items = [DummyRatingItem()]

    rating = DummyRating()
    quota = [QuotaDecision(metric="calls", action="allow", used=1, soft=10, hard=20)]
    snap = build_snapshot(
        version="v1",
        tenant="tenant-1",
        witness_csv_path="/tmp/test@example.com",
        witness_rows=1,
        witness_csv_sha256="abc",
        buckets={},
        deltas_by_metric={},
        rating=rating,
        quota=quota,
        budget_level="ok",
        budget_spent=0,
        budget_limit=1,
        anomaly_is_spike=False,
        anomaly_ewma=0,
        anomaly_ratio=0,
    )
    assert "@" not in snap.witness["csv_path"]
