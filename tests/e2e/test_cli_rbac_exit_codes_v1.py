import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.gate_aj]


def test_rbac_denied(monkeypatch, tmp_path):
    slo_path = tmp_path / "slo.json"
    slo_path.write_text(json.dumps({"budget": {"allow_levels": ["ok"]}}), encoding="utf-8")

    ev_path = tmp_path / "evidence.json"
    ev_payload = {
        "meta": {},
        "witness": {},
        "usage": {},
        "rating": {},
        "quota": {},
        "budget": {},
        "anomaly": {},
        "integrity": {},
    }
    ev_path.write_text(json.dumps(ev_payload), encoding="utf-8")

    providers_path = tmp_path / "providers.yaml"
    providers_path.write_text(yaml.safe_dump({"providers": [{"id": "local-a", "type": "local"}]}), encoding="utf-8")

    monkeypatch.setenv("DECISIONOS_ENFORCE_RBAC", "1")
    monkeypatch.setenv("DECISIONOS_RBAC_DENY", f"judge.run:slo:{slo_path.name}")

    cmd = [
        sys.executable,
        "-m",
        "apps.cli.dosctl.judge_quorum",
        "--slo",
        str(slo_path),
        "--evidence",
        str(ev_path),
        "--providers",
        str(providers_path),
        "--quorum",
        "1/1",
    ]
    rc = subprocess.call(cmd)
    assert rc == 3
