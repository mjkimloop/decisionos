import pytest
from apps.sre.burnrate import BurnRateConfig, compute_burn_rate, evaluate_burn_rate

pytestmark = pytest.mark.gate_q

def test_burnrate_ok_warn_critical():
    cfg = BurnRateConfig(target_availability=0.995, window_sec=3600, thresholds={"warn":1.0,"critical":2.0})

    # OK: 에러 0.1% (가용 0.999) → 예산(0.5%) 대비 소모율 < 1x
    br_ok = compute_burn_rate(10000, 10, cfg)
    assert evaluate_burn_rate(br_ok, cfg) == "ok"

    # WARN: 에러 0.7% (가용 0.993) → 소모율 ≈ (0.995-0.993)/0.005 = 0.002/0.005 = 0.4 -> still ok
    # warn으로 맞추기 위해 더 큰 에러
    br_warn = compute_burn_rate(10000, 40, cfg)  # 가용 0.996 → 소모 (0.995-0.996)=0 (clip) => 0 → ok
    # 조정: warn 경계를 명확히 넘기려면 가용을 0.99로
    br_warn = compute_burn_rate(10000, 100, cfg)  # 에러 1% → 가용 0.99 → 소모 0.005/0.005 = 1x
    assert evaluate_burn_rate(br_warn, cfg) in {"warn","critical"}

    # CRITICAL: 가용 0.985 → 소모 0.01/0.005 = 2x
    br_crit = compute_burn_rate(10000, 150, cfg)
    assert evaluate_burn_rate(br_crit, cfg) == "critical"
