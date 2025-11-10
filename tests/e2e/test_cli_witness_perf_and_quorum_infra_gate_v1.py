import json
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.gate_aj]


def _write(path: Path, data: dict):
    path.write_text(json.dumps(data), encoding="utf-8")


def _base_evidence(perf_judge: dict) -> dict:
    evidence = {
        "meta": {"tenant": "demo"},
        "witness": {"csv_sha256": "abc"},
        "usage": {},
        "rating": {},
        "quota": {},
        "budget": {"level": "ok", "spent": 0.1, "limit": 1.0},
        "anomaly": {"is_spike": False},
        "perf": None,
        "perf_judge": perf_judge,
    }
    core = {
        k: evidence[k]
        for k in ["meta", "witness", "usage", "rating", "quota", "budget", "anomaly"]
    }
    evidence["integrity"] = {
        "signature_sha256": hashlib.sha256(
            json.dumps(core, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
    }
    return evidence


def test_cli_witness_perf_and_quorum(tmp_path, monkeypatch):
    csv_path = tmp_path / "reqlog.csv"
    csv_path.write_text(
        "\n".join(
            [
                "ts,status,latency_ms,signature_error",
                "2025-11-10T00:00:00Z,200,100,0",
                "2025-11-10T00:00:01Z,200,90,0",
                "2025-11-10T00:00:02Z,503,1200,0",
                "2025-11-10T00:00:03Z,200,80,0",
            ]
        ),
        encoding="utf-8",
    )
    out_perf = tmp_path / "perf.json"
    cmd_perf = [
        sys.executable,
        "-m",
        "apps.cli.dosctl.witness_judge_perf",
        "--csv",
        str(csv_path),
        "--out",
        str(out_perf),
    ]
    assert subprocess.call(cmd_perf) == 0
    perf_data = json.loads(out_perf.read_text(encoding="utf-8"))

    evidence = _base_evidence(perf_data)
    evidence_path = tmp_path / "evidence.json"
    _write(evidence_path, evidence)

    providers_path = tmp_path / "providers.yaml"
    providers_path.write_text('providers:\n  - id: local-a\n    type: local\n', encoding="utf-8")

    slo_path = tmp_path / "slo.json"
    slo_conf = {
        "judge_infra": {
            "latency": {"max_p95_ms": 1500, "max_p99_ms": 2500},
            "availability": {"min_availability": 0.7},
            "sig": {"max_sig_error_rate": 0.1},
        }
    }
    _write(slo_path, slo_conf)

    cmd_pass = [
        sys.executable,
        "-m",
        "apps.cli.dosctl.judge_quorum",
        "--slo",
        str(slo_path),
        "--evidence",
        str(evidence_path),
        "--providers",
        str(providers_path),
        "--quorum",
        "1/1",
    ]
    assert subprocess.call(cmd_pass) == 0

    # force failure by bumping sig error rate
    perf_data["signature_error_rate"] = 0.5
    _write(evidence_path, _base_evidence(perf_data))
    assert subprocess.call(cmd_pass) == 2
