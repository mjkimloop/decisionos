"""
Test Shadow Sampler Hysteresis v1
히스테리시스 동작 테스트
"""
import pytest
from datetime import datetime, timedelta, timezone
from apps.experiment.shadow_sampler import ShadowSampler, SamplerConfig, Hysteresis


@pytest.mark.gate_u
def test_load_spike_down():
    """부하 급등 → 즉시 샘플링% 감소"""
    config = SamplerConfig(
        min_pct=1,
        max_pct=50,
        hysteresis=Hysteresis(up_ms=900, down_ms=300)
    )

    sampler = ShadowSampler(config)
    sampler._pct = 20  # 초기값 설정

    # 400ms 전으로 last_change 설정 (down_ms=300ms 초과)
    now = datetime.now(timezone.utc)
    sampler._last_change = now - timedelta(milliseconds=400)

    # 부하 급등 신호
    signals = {"cpu": 0.9, "queue_depth": 150}

    # 감소 예상
    new_pct = sampler.update(signals, now)
    assert new_pct < 20
    assert new_pct == 15  # 20 - 5 = 15


@pytest.mark.gate_u
def test_load_relief_up():
    """부하 완화 → 지연 후 샘플링% 증가"""
    config = SamplerConfig(
        min_pct=1,
        max_pct=50,
        hysteresis=Hysteresis(up_ms=900, down_ms=300)
    )

    sampler = ShadowSampler(config)
    sampler._pct = 10

    now = datetime.now(timezone.utc)

    # 500ms 전 - up_ms=900ms 미만이므로 변화 없어야 함
    sampler._last_change = now - timedelta(milliseconds=500)
    signals = {"cpu": 0.2, "queue_depth": 5}

    new_pct1 = sampler.update(signals, now)
    assert new_pct1 == 10  # 변화 없음

    # 1000ms 전 - up_ms=900ms 초과이므로 증가해야 함
    sampler._last_change = now - timedelta(milliseconds=1000)
    new_pct2 = sampler.update(signals, now)
    assert new_pct2 > 10
    assert new_pct2 == 15  # 10 + 5 = 15


@pytest.mark.gate_u
def test_hysteresis_timing():
    """up_ms > down_ms 검증"""
    config = SamplerConfig(
        min_pct=1,
        max_pct=50,
        hysteresis=Hysteresis(up_ms=900, down_ms=300)
    )

    # 히스테리시스 설정 검증
    assert config.hysteresis.up_ms > config.hysteresis.down_ms

    now = datetime.now(timezone.utc)

    # 감소는 빠름 (300ms)
    sampler1 = ShadowSampler(config)
    sampler1._pct = 20
    sampler1._last_change = now - timedelta(milliseconds=400)  # 400ms 전
    high_load_signals = {"cpu": 0.9, "queue_depth": 150}

    new_pct_down = sampler1.update(high_load_signals, now)
    assert new_pct_down < 20  # 감소됨

    # 증가는 느림 (900ms)
    sampler2 = ShadowSampler(config)
    sampler2._pct = 10
    sampler2._last_change = now - timedelta(milliseconds=400)  # 400ms 전
    low_load_signals = {"cpu": 0.2, "queue_depth": 5}

    new_pct_up = sampler2.update(low_load_signals, now)
    assert new_pct_up == 10  # 아직 변화 없음
