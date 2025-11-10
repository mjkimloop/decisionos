import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.gate_aj]


def _providers(path: Path):
    path.write_text("providers:\n  - id: local-a\n    type: local\n", encoding="utf-8")
    return path


def _merge_canary(evidence_path: Path, canary_json: Path):
    data = json.loads(evidence_path.read_text(encoding="utf-8"))
    canary = json.loads(canary_json.read_text(encoding="utf-8"))
    data["canary"] = canary
    core = {k: data[k] for k in ["meta", "witness", "usage", "rating", "quota", "budget", "anomaly"]}
    for block in ("perf", "perf_judge", "judges", "canary"):
        if data.get(block) is not None:
            core[block] = data[block]
    data["integrity"]["signature_sha256"] = __import__("hashlib").sha256(
        json.dumps(core, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    evidence_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_cli_canary_gate(tmp_path: Path):
    shadow_dir = tmp_path / "shadow"
    cmd_capture = [
        sys.executable,
        "-m",
        "apps.cli.dosctl.shadow_capture",
        "--out",
        str(shadow_dir),
        "--samples",
        "20000",
    ]
    assert subprocess.call(cmd_capture) == 0

    canary_json = tmp_path / "canary.json"
    cmd_compare = [
        sys.executable,
        "-m",
        "apps.cli.dosctl.canary_compare",
        "--control",
        str(shadow_dir / "control.csv"),
        "--canary",
        str(shadow_dir / "canary.csv"),
        "--out",
        str(canary_json),
    ]
    assert subprocess.call(cmd_compare) == 0

    evidence_path = tmp_path / "evidence.json"
    base = Path("evidence/sample_release_gate.json").read_text(encoding="utf-8")
    evidence_path.write_text(base, encoding="utf-8")
    _merge_canary(evidence_path, canary_json)

    providers_path = _providers(tmp_path / "providers.yaml")
    cmd_judge = [
        sys.executable,
        "-m",
        "apps.cli.dosctl.judge_quorum",
        "--slo",
        "configs/slo/slo-canary.json",
        "--evidence",
        str(evidence_path),
        "--providers",
        str(providers_path),
        "--quorum",
        "1/1",
    ]
    assert subprocess.call(cmd_judge) == 0

    bad = json.loads(canary_json.read_text(encoding="utf-8"))
    bad["deltas"]["p95_rel"] = 0.5
    canary_json.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    _merge_canary(evidence_path, canary_json)
    assert subprocess.call(cmd_judge) == 2
