from __future__ import annotations

import json
from pathlib import Path

from jobs.obs.reconcile.backfill_runner import run_backfill_reconcile


SLO_CONFIG = {
    "routes": [],
    "measurement_quorum_tolerances": {
        "latency_p95_delta_pct": 2.0,
        "err_rate_delta_pp": 0.1,
        "cost_krw_delta_pct": 1.0,
        "citation_cov_delta_pp": 0.5,
        "parity_delta_pp": 0.2,
    },
}


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_raw(path: Path, events):
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")


def make_primary_witness(path: Path) -> None:
    primary = {
        "period_start": "2025-11-07T00:00:00Z",
        "period_end": "2025-11-07T01:00:00Z",
        "sample_n": 10,
        "coverage_ratio": 1.0,
        "dropped_spans": 0,
        "latency_p95": 1000,
        "latency_p99": 1100,
        "err_rate": 0.01,
        "cost_krw": 10,
        "citation_cov": 0.98,
        "parity_delta": 0.05,
        "build_id": "b",
        "commit_sha": "sha",
        "source_id": "primary",
        "sha256": "abc",
    }
    write_json(path, primary)


def test_backfill_runner_detects_discrepancy(tmp_path: Path):
    witness_path = tmp_path / "primary.json"
    raw_path = tmp_path / "raw.jsonl"
    slo_path = tmp_path / "slo.json"
    make_primary_witness(witness_path)
    write_raw(
        raw_path,
        [
            {"latency_ms": 1500, "err": 1, "cost_krw": 30, "cite_ok": 0, "parity_delta": 0.4},
            {"latency_ms": 1600, "err": 1, "cost_krw": 30, "cite_ok": 0, "parity_delta": 0.4},
        ],
    )
    write_json(slo_path, SLO_CONFIG)

    report = run_backfill_reconcile(witness_path, raw_path, slo_path, tmp_path)
    assert report["status"] == "FAIL"
    csv_path = tmp_path / "discrepancies.csv"
    assert csv_path.exists()
    csv_text = csv_path.read_text(encoding="utf-8")
    assert "latency_p95" in csv_text


def test_backfill_runner_passes_within_tolerance(tmp_path: Path):
    witness_path = tmp_path / "primary.json"
    raw_path = tmp_path / "raw.jsonl"
    slo_path = tmp_path / "slo.json"
    make_primary_witness(witness_path)
    write_raw(
        raw_path,
        [
            {"latency_ms": 950, "err": 0, "cost_krw": 10, "cite_ok": 1, "parity_delta": 0.04}
            for _ in range(20)
        ],
    )
    write_json(slo_path, SLO_CONFIG)

    report = run_backfill_reconcile(witness_path, raw_path, slo_path, tmp_path)
    assert report["status"] == "PASS"
    csv_path = tmp_path / "discrepancies.csv"
    content = csv_path.read_text(encoding="utf-8")
    assert "PASS" in content
