import json
import subprocess
import sys


def test_gameday_latency_and_report(tmp_path):
    latency = tmp_path / "latency.json"
    error = tmp_path / "error.json"
    judge = tmp_path / "judge.json"
    subprocess.run(
        [sys.executable, "-m", "scripts.gameday.run_scenario", "--scenario", "latency_spike", "--out", str(latency)],
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "scripts.gameday.run_scenario", "--scenario", "error_spike", "--out", str(error)],
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "scripts.gameday.run_scenario", "--scenario", "judge_unavailable", "--out", str(judge)],
        check=True,
    )
    assert latency.exists()
    data = json.loads(latency.read_text())
    assert data["scenario"] == "latency_spike"
    report = tmp_path / "report.md"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.gameday.report_md",
            "--inputs",
            str(latency),
            str(error),
            str(judge),
            "--out",
            str(report),
        ],
        check=True,
    )
    assert "GameDay" in report.read_text()
