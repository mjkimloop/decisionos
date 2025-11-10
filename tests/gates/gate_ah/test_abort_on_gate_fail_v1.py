import json
import subprocess
import sys
from pathlib import Path

import pytest

from apps.experiment.stage_file import read_stage_with_hash, write_stage_atomic

pytestmark = [pytest.mark.gate_ah]

if sys.platform.startswith("win"):
    pytest.skip("requires bash environment", allow_module_level=True)


def test_abort_on_gate_fail_triggers_abort(tmp_path, monkeypatch):
    stage = tmp_path / "desired_stage.txt"
    write_stage_atomic("canary", str(stage))
    monkeypatch.setenv("STAGE_PATH", str(stage))
    monkeypatch.setenv("ROLLOUT_MODE", "none")

    slo = tmp_path / "missing-slo.json"
    evidence = tmp_path / "evidence.json"
    providers = tmp_path / "providers.yaml"

    evidence.write_text(
        json.dumps(
            {
                "meta": {},
                "witness": {},
                "usage": {},
                "rating": {},
                "quota": {},
                "budget": {},
                "anomaly": {},
                "integrity": {"signature_sha256": "x"},
            }
        ),
        encoding="utf-8",
    )
    providers.write_text("providers: []", encoding="utf-8")

    rc = subprocess.run(
        [
            "bash",
            "pipeline/release/abort_on_gate_fail.sh",
            str(slo),
            str(evidence),
            str(providers),
            "1/1",
        ],
        check=False,
        cwd=Path.cwd(),
    ).returncode
    assert rc == 2
    state = read_stage_with_hash(str(stage))
    assert state.stage == "abort"
