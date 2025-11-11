import pytest
import os

@pytest.mark.gate_ops
def test_alert_gate_triggers(monkeypatch):
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "ops:alert")
    called = {}

    def fake_post(url, payload):
        called["ok"] = True
        return 200

    import apps.ops.alerts.slack as s
    monkeypatch.setattr(s, "post_card", fake_post)
    monkeypatch.setenv("ALERTS_SLACK_WEBHOOK", "http://example")

    from apps.ops.alerts.gate import run_alert_gate

    summary = {
        "buckets": [{
            "end": "2025-01-01T10:00:00Z",
            "anomaly": {"triggered": True, "flags": [{}]},
            "bucket_score": 6.0
        }]
    }
    assert run_alert_gate(summary) == 0
    assert called.get("ok", False)

@pytest.mark.gate_ops
def test_alert_gate_rbac_denied(monkeypatch):
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "ops:read")  # No ops:alert

    from apps.ops.alerts.gate import run_alert_gate

    summary = {"buckets": []}
    assert run_alert_gate(summary) == 3  # RBAC denied
