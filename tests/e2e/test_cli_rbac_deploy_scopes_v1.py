import subprocess
import sys

import pytest

pytestmark = [pytest.mark.gate_aj]

if sys.platform.startswith("win"):
    pytest.skip("requires bash environment", allow_module_level=True)


def test_rbac_promote_denied(monkeypatch, tmp_path):
    stage = tmp_path / "stage.txt"
    monkeypatch.setenv("STAGE_PATH", str(stage))
    monkeypatch.setenv("ROLLOUT_MODE", "none")
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "judge:run")
    rc = subprocess.call(["bash", "pipeline/release/promote.sh"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert rc != 0
