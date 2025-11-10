import tempfile
from pathlib import Path

import pytest

pytestmark = [pytest.mark.gate_ah]

from apps.experiment.controller import TrafficController


def _policy(tmp_path: Path, stages=None):
    data = {
        "stages": stages or [10, 50, 100],
        "hold_minutes": 0,
        "hash_key": "header:X-Canary-Key",
    }
    path = tmp_path / "policy.yaml"
    path.write_text(
        f"stages: {data['stages']}\nhold_minutes: 0\nmax_parallel: 1\nrollback_on_fail: true\nhash_key: \"header:X-Canary-Key\"\n",
        encoding="utf-8",
    )
    return str(path)


def test_sticky_routing(tmp_path):
    controller = TrafficController(policy_path=_policy(tmp_path, [50]))
    controller.set_stage(50)
    headers = {"X-Canary-Key": "user-123"}
    first = controller.route(headers)
    second = controller.route(headers)
    assert first == second


def test_stage_progress_and_rollback(tmp_path):
    controller = TrafficController(policy_path=_policy(tmp_path, [10, 50]))
    controller.register_result(success=True)
    assert controller.current_percentage() == 50
    controller.register_result(success=False)
    assert controller.current_percentage() == 0
