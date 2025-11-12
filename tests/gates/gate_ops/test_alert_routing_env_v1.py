import pytest
from apps.alerts.router import resolve_channel

CFG = {
    "default_channel": "#decisionos-deploy",
    "env_channels": {"staging":"#decisionos-staging"},
    "routing": {"rules":[{"match":{"reason_prefix":"infra."},"channel":"#decisionos-infra"}]}
}

@pytest.mark.gate_ops
def test_route_by_reason_over_env():
    ch = resolve_channel("staging", "infra.latency_p95_over", CFG)
    assert ch == "#decisionos-infra"

@pytest.mark.gate_ops
def test_route_by_env_fallback():
    ch = resolve_channel("staging", "misc.something", CFG)
    assert ch == "#decisionos-staging"
