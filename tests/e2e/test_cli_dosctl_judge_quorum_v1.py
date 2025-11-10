import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.gate_aj]


def _write(path: Path, data, mode: str = "json"):
    if mode == "json":
        path.write_text(json.dumps(data), encoding="utf-8")
    else:
        path.write_text(yaml.safe_dump(data), encoding="utf-8")


def _signed_evidence(budget_level: str) -> dict:
    evidence = {
        "meta": {"version": "v1", "generated_at": "2025-01-01T00:00:00Z", "tenant": "tenant-x"},
        "witness": {"csv_path": "w.csv", "csv_sha256": "abc", "rows": 1},
        "usage": {"buckets": {}, "deltas_by_metric": {}},
        "rating": {"subtotal": 0.0, "items": []},
        "quota": {"decisions": {}},
        "budget": {"level": budget_level, "spent": 0.0, "limit": 1.0},
        "anomaly": {"is_spike": False, "ewma": 0.0, "ratio": 0.0},
    }
    core = {k: evidence[k] for k in ["meta", "witness", "usage", "rating", "quota", "budget", "anomaly"]}
    signature_bytes = json.dumps(core, ensure_ascii=False, sort_keys=True).encode("utf-8")
    evidence["integrity"] = {"signature_sha256": __import__("hashlib").sha256(signature_bytes).hexdigest()}
    return evidence


def test_cli_exit_codes(tmp_path):
    slo = {"quorum": {"fail_closed_on_degrade": True}}
    ok_ev = _signed_evidence("ok")
    bad_ev = _signed_evidence("exceeded")
    providers = {"providers": [{"id": "local-a", "type": "local"}]}

    slo_path = tmp_path / "slo.json"
    ev_ok_path = tmp_path / "ok.json"
    ev_bad_path = tmp_path / "bad.json"
    providers_path = tmp_path / "providers.yaml"

    _write(slo_path, slo)
    _write(ev_ok_path, ok_ev)
    _write(ev_bad_path, bad_ev)
    _write(providers_path, providers, mode="yaml")

    base_cmd = [
        sys.executable,
        "-m",
        "apps.cli.dosctl.judge_quorum",
        "--slo",
        str(slo_path),
        "--providers",
        str(providers_path),
        "--quorum",
        "1/1",
        "--attach-evidence",
    ]

    cmd_pass = base_cmd + ["--evidence", str(ev_ok_path)]
    res_pass = subprocess.run(cmd_pass, capture_output=True, text=True)
    assert res_pass.returncode == 0, res_pass.stderr

    cmd_fail = base_cmd + ["--evidence", str(ev_bad_path)]
    res_fail = subprocess.run(cmd_fail, capture_output=True, text=True)
    assert res_fail.returncode == 2, res_fail.stdout + res_fail.stderr
