import json
from pathlib import Path

import pytest

from apps.ops.reports.reason_trend import aggregate_reason_trend

pytestmark = [pytest.mark.gate_t]


def test_reason_trend_aggregates(tmp_path):
    evdir = tmp_path / "evidence"
    evdir.mkdir()

    evidence_a = {
        "meta": {"generated_at": "2025-11-10T12:00:00Z"},
        "judges": [{"reasons": [{"code": "perf.p95_over"}]}],
    }
    evidence_b = {
        "meta": {"generated_at": "2025-11-11T02:00:00Z"},
        "judges": [{"reasons": [{"code": "perf.p95_over"}, {"code": "quota.forbidden_action"}]}],
    }

    (evdir / "evidence-a.json").write_text(json.dumps(evidence_a), encoding="utf-8")
    (evdir / "evidence-b.json").write_text(json.dumps(evidence_b), encoding="utf-8")

    trend = aggregate_reason_trend(str(evdir), days=7)
    totals = dict(trend["total_top"])
    assert totals["perf.p95_over"] == 2
    assert totals["quota.forbidden_action"] == 1
    assert trend.get("last_updated") is not None
