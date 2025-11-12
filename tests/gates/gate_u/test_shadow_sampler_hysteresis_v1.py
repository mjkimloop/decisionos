"""
Test Shadow Sampler Hysteresis v1
히스테리시스 동작 테스트
"""
import pytest
import time
from apps.experiment.shadow_sampler import adjust_sample_pct


@pytest.mark.gate_u
def test_load_spike_down():
    """부하 급등 → 즉시 샘플링% 감소"""
    config = {
        "min_pct": 1,
        "max_pct": 50,
        "hysteresis": {
            "up_ms": 900,  # 증가는 느리게
            "down_ms": 300  # 감소는 빠르게
        }
    }

    # 부하 급등 신호 (load_score > 0.7)
    signals = {
        "qps": 1200,  # 높음 (1200/1000 = 1.2)
        "cpu": 0.9,   # 높음
        "queue_depth": 150  # 높음 (150/100 = 1.5)
    }

    current_pct = 20.0
    start_ts = time.time() - 0.5  # 500ms 전에 변경됨

    # down_ms=300ms 지난 상태이므로 즉시 감소
    new_pct, new_ts = adjust_sample_pct(current_pct, signals, config, start_ts)

    # 20% * 0.8 = 16%
    assert new_pct < current_pct
    assert abs(new_pct - 16.0) < 0.1
    assert new_ts > start_ts


@pytest.mark.gate_u
def test_load_relief_up():
    """부하 완화 → 지연 후 샘플링% 증가"""
    config = {
        "min_pct": 1,
        "max_pct": 50,
        "hysteresis": {
            "up_ms": 900,  # 증가는 느리게
            "down_ms": 300
        }
    }

    # 부하 낮음 신호 (load_score < 0.3)
    signals = {
        "qps": 100,  # 낮음
        "cpu": 0.2,  # 낮음
        "queue_depth": 5  # 낮음
    }

    current_pct = 10.0
    start_ts = time.time() - 0.5  # 500ms 전

    # up_ms=900ms 아직 안 지나서 변화 없음
    new_pct1, new_ts1 = adjust_sample_pct(current_pct, signals, config, start_ts)
    assert new_pct1 == current_pct
    assert new_ts1 == start_ts

    # 1초 전으로 설정 (900ms 초과)
    start_ts = time.time() - 1.0

    # 이제 증가
    new_pct2, new_ts2 = adjust_sample_pct(current_pct, signals, config, start_ts)
    # 10% * 1.1 = 11%
    assert new_pct2 > current_pct
    assert abs(new_pct2 - 11.0) < 0.1
    assert new_ts2 > start_ts


@pytest.mark.gate_u
def test_hysteresis_timing():
    """up_ms > down_ms 검증"""
    config = {
        "min_pct": 1,
        "max_pct": 50,
        "hysteresis": {
            "up_ms": 900,
            "down_ms": 300
        }
    }

    # 히스테리시스 설정 검증
    assert config["hysteresis"]["up_ms"] > config["hysteresis"]["down_ms"]

    # 감소는 빠름 (300ms)
    high_load_signals = {"qps": 1200, "cpu": 0.9, "queue_depth": 150}
    start_ts = time.time() - 0.4  # 400ms 전

    new_pct_down, _ = adjust_sample_pct(20.0, high_load_signals, config, start_ts)
    assert new_pct_down < 20.0  # 감소됨

    # 증가는 느림 (900ms)
    low_load_signals = {"qps": 100, "cpu": 0.2, "queue_depth": 5}
    start_ts2 = time.time() - 0.4  # 400ms 전

    new_pct_up, _ = adjust_sample_pct(10.0, low_load_signals, config, start_ts2)
    assert new_pct_up == 10.0  # 아직 변화 없음
