import json
import os
import subprocess
import sys


def test_burn_gate_sets_freeze_flag(tmp_path, monkeypatch):
    policy = tmp_path / "policy.yaml"
    policy.write_text(
        """
windows:
  - name: "5m"
    duration: "5m"
    fast_threshold: 2.0
    slow_threshold: 4.0
metrics:
  error_rate:
    objective_availability: 0.99
""",
        encoding="utf-8",
    )
    samples = tmp_path / "samples.json"
    samples.write_text(
        json.dumps({"samples": [{"ts": 1700000000, "requests": 100, "errors": 20}]}),
        encoding="utf-8",
    )
    report = tmp_path / "report.json"
    freeze_flag = tmp_path / "freeze.flag"
    monkeypatch.setenv("DECISIONOS_FREEZE_FILE", str(freeze_flag))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "jobs.burn_alert_gate",
            "--policy",
            str(policy),
            "--samples",
            str(samples),
            "--report",
            str(report),
            "--reasons-json",
            str(tmp_path / "reasons.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert report.exists()
    assert freeze_flag.exists()
