import pytest
import os, json
from datetime import datetime, timezone

@pytest.mark.gate_ops
def test_resolve_by_hour_and_dow(tmp_path):
    p = tmp_path/"th.json"
    obj = {
        "bucket": "hour",
        "by_hour": {"10": {"perf": {"mean": 1.0, "std": 0.1}}, "23": {"perf": {"mean": 5.0, "std": 0.5}}},
        "by_dow": {}
    }
    p.write_text(json.dumps(obj), encoding="utf-8")

    from apps.ops.cards.thresholds_seasonal import load_seasonal, resolve_for
    st = load_seasonal(str(p))
    assert st is not None

    t10 = datetime(2025, 1, 1, 10, tzinfo=timezone.utc)
    t23 = datetime(2025, 1, 1, 23, tzinfo=timezone.utc)

    resolved_10 = resolve_for(t10, "auto", st)
    assert resolved_10 is not None
    assert "perf" in resolved_10
    assert resolved_10["perf"].mean == 1.0

    resolved_23 = resolve_for(t23, "hour", st)
    assert resolved_23 is not None
    assert "perf" in resolved_23
    assert resolved_23["perf"].mean == 5.0
