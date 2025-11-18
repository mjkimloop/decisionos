from pathlib import Path

from apps.ops import metrics_burn


def test_compute_burn_report(tmp_path):
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
  latency_p95:
    objective_ms: 400
""",
        encoding="utf-8",
    )
    samples = tmp_path / "samples.json"
    samples.write_text(
        '{"samples": [{"ts": 1700000000, "requests": 1000, "errors": 10, "latency_p95": 450}]}',
        encoding="utf-8",
    )
    report = metrics_burn.compute_burn_report(policy_path=str(policy), sample_path=str(samples))
    assert report["windows"]
    win = report["windows"][0]
    assert win["name"] == "5m"
    assert win["state"] == "ok"
    assert "error_rate" in win["metrics"]
    assert win["metrics"]["error_rate"]["burn"] >= 1.0
