import pytest

from apps.experiment.controller import TrafficController
from apps.ops import freeze as freeze_guard


def test_controller_blocks_stage_during_freeze(policy_keys, monkeypatch):
    monkeypatch.setenv("DECISIONOS_SERVICE", "ops-api")
    monkeypatch.setenv("_FREEZE_NOW", "2025-11-22T00:00:00Z")
    blocked, _ = freeze_guard.is_freeze_active(service="ops-api", labels=[])
    assert blocked
    with pytest.raises(RuntimeError):
        TrafficController(stage_file_path="var/rollout/test_stage.txt").promote()
