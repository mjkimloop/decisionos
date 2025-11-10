import os, json, subprocess, sys
import pytest
from apps.experiment.stage_file import write_stage_atomic, read_stage_with_hash

pytestmark = [pytest.mark.gate_ah]

if sys.platform.startswith("win"):
    pytest.skip("requires bash environment", allow_module_level=True)

def test_abort_on_latency_spike(tmp_path, monkeypatch):
    stage = tmp_path / "desired_stage.txt"
    write_stage_atomic("canary", str(stage))
    monkeypatch.setenv("STAGE_PATH", str(stage))
    # 카오스 주입: p95 크게
    subprocess.check_call(["bash","-c","pipeline/release/chaos_inject.sh --latency-p95=2000"])
    # 게이트 스텝이 실패한다고 가정하고 abort 스크립트 호출
    rc = subprocess.call(["bash","-c","pipeline/release/abort_on_gate_fail.sh"])
    assert rc == 1
    s = read_stage_with_hash(str(stage))
    assert s.stage == "stable"
