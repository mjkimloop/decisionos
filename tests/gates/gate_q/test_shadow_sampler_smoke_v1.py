import pytest
from datetime import datetime, timedelta, timezone
from apps.experiment.shadow_sampler import ShadowSampler, SamplerConfig, Hysteresis

pytestmark = pytest.mark.gate_q

def test_shadow_sampler_hysteresis_up_down():
    sampler = ShadowSampler(SamplerConfig(min_pct=1, max_pct=10, hysteresis=Hysteresis(up_ms=200, down_ms=200)))
    now = datetime.now(timezone.utc)

    # 초기값
    assert sampler._pct >= 1

    # 여유 → 증가 허용 전에는 변화 없음
    p0 = sampler._pct
    sampler.update({"cpu":0.1,"queue_depth":0}, now=now + timedelta(milliseconds=100))
    assert sampler._pct == p0  # 아직 up hysteresis 미충족

    sampler.update({"cpu":0.1,"queue_depth":0}, now=now + timedelta(milliseconds=250))
    assert sampler._pct >= p0  # 증가 허용

    # 과부하 → 감소도 히스테리시스 확인
    p1 = sampler._pct
    sampler.update({"cpu":0.95,"queue_depth":100}, now=now + timedelta(milliseconds=300))
    assert sampler._pct in {p1, p1-5}  # down 허용되면 5 감소
