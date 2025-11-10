import json
import sys
from pathlib import Path

import pytest

from apps.experiment import stage_file

pytestmark = [pytest.mark.gate_ah]

if sys.platform.startswith("win"):
    pytest.skip("requires bash environment", allow_module_level=True)


def test_manifest_signature_mismatch_repairs(monkeypatch, tmp_path):
    monkeypatch.setenv("DECISIONOS_STAGE_KEY", "sig-test-key")
    monkeypatch.setenv("DECISIONOS_STAGE_KEY_ID", "sig-test")
    monkeypatch.chdir(tmp_path)
    Path("var/rollout").mkdir(parents=True, exist_ok=True)
    stage_file.write_stage_atomic("canary")

    manifest_path = Path(stage_file.manifest_path())
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sig_hmac"] = "deadbeef"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    state = stage_file.read_stage_with_hash()
    assert state.stage == "stable"
    repaired_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert repaired_manifest["sig_hmac"] != "deadbeef"
