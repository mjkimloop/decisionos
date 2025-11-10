import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.gate_aj, pytest.mark.gate_t]

from apps.obs.witness.canary_compare import compare
from apps.obs.witness.shadow import ShadowRecorder, mirror_request
from apps.obs.evidence.snapshot import build_snapshot
from apps.judge.slo_judge import evaluate


def _write_samples(base: Path):
    recorder = ShadowRecorder(base / "control.csv", base / "canary.csv")
    for i in range(6000):
        bucket = "canary" if i % 5 == 0 else "control"
        status = 503 if i % 41 == 0 else 200
        latency = 100 if bucket == "control" else 106
        mirror_request(bucket, status, latency, recorder=recorder, sample_rate=1.0)
    return base / "control.csv", base / "canary.csv"


def test_canary_compare_and_judge(tmp_path: Path):
    control_csv, canary_csv = _write_samples(tmp_path)
    canary_block = compare(control_csv, canary_csv)

    evidence = build_snapshot(
        version="v0.5.11k",
        tenant="demo",
        witness_csv_path="witness.csv",
        witness_rows=1,
        witness_csv_sha256="abc",
        buckets={},
        deltas_by_metric={},
        rating=type("Dummy", (), {"subtotal": 0, "items": []})(),
        quota=[],
        budget_level="ok",
        budget_spent=0.1,
        budget_limit=1.0,
        anomaly_is_spike=False,
        anomaly_ewma=0.0,
        anomaly_ratio=0.0,
        perf=None,
        perf_judge=None,
        judges=None,
        canary=canary_block,
    )

    slo = json.loads(Path("configs/slo/slo-canary.json").read_text(encoding="utf-8"))
    decision, reasons = evaluate(json.loads(evidence.to_json()), slo)
    assert decision == "pass"
