import pytest
from apps.ops.metrics import observe_risk_score, observe_burn_rate, set_shadow_pct, inc_alert

pytestmark = pytest.mark.gate_q

def test_ops_metrics_no_prometheus_installed_noop():
    # prometheus_client 미설치 환경에서도 예외 없이 호출 가능해야 함
    observe_risk_score(0.42)
    observe_burn_rate(0.7)
    set_shadow_pct(7)
    inc_alert("warn")
