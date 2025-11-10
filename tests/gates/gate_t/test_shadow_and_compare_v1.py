from pathlib import Path

import pytest

pytestmark = [pytest.mark.gate_t]

from apps.obs.witness.canary_compare import compare


def test_canary_compare_basic(tmp_path: Path):
    control = tmp_path / "control.csv"
    canary = tmp_path / "canary.csv"
    control.write_text(
        "ts,status,latency_ms,signature_error,payload_size\n"
        "t0,200,100,0,10\n"
        "t1,503,150,0,10\n",
        encoding="utf-8",
    )
    canary.write_text(
        "ts,status,latency_ms,signature_error,payload_size\n"
        "t0,200,120,0,10\n"
        "t1,200,140,1,10\n",
        encoding="utf-8",
    )
    summary = compare(control, canary)
    assert summary["control_perf"]["count"] == 2
    assert summary["canary_perf"]["count"] == 2
    assert summary["deltas"]["p95_rel"] <= 0.5
