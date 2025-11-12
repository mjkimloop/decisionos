"""
Shadow Sampler (Adaptive Sampling)
QPS/CPU/Queue 기반 적응형 샘플링 비율 조정 (히스테리시스)
"""
import json
import os
import time
from typing import Dict, Any


def load_sampler_config(path: str = "configs/shadow/sampler.json") -> Dict[str, Any]:
    """샘플러 설정 로드"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Sampler config not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def adjust_sample_pct(
    current_pct: float,
    signals: Dict[str, Any],
    config: Dict[str, Any],
    last_change_ts: float = 0.0
) -> tuple[float, float]:
    """
    히스테리시스 적용하여 샘플링 비율 조정

    Args:
        current_pct: 현재 샘플링 비율 (%)
        signals: 부하 신호 (qps, cpu, queue_depth 등)
        config: 샘플러 설정 (min_pct, max_pct, hysteresis)
        last_change_ts: 마지막 변경 시각 (초 단위 timestamp)

    Returns:
        (new_pct, new_timestamp): 새 샘플링 비율과 변경 시각
    """
    min_pct = config.get("min_pct", 1)
    max_pct = config.get("max_pct", 50)
    hysteresis = config.get("hysteresis", {})
    up_ms = hysteresis.get("up_ms", 900)
    down_ms = hysteresis.get("down_ms", 300)

    # 부하 점수 계산 (0~1 범위)
    # 간단한 구현: qps, cpu, queue_depth를 정규화하여 평균
    load_score = 0.0
    count = 0

    qps = signals.get("qps", 0)
    cpu = signals.get("cpu", 0.0)
    queue_depth = signals.get("queue_depth", 0)

    # QPS 정규화 (예: 1000 이상이면 1.0)
    if qps > 0:
        load_score += min(qps / 1000.0, 1.0)
        count += 1

    # CPU 정규화 (0~1 범위로 가정)
    if cpu > 0:
        load_score += min(cpu, 1.0)
        count += 1

    # Queue depth 정규화 (예: 100 이상이면 1.0)
    if queue_depth > 0:
        load_score += min(queue_depth / 100.0, 1.0)
        count += 1

    if count > 0:
        load_score /= count

    # 부하가 높으면 샘플링 비율 감소 (즉시)
    # 부하가 낮으면 샘플링 비율 증가 (지연)
    current_ts = time.time()
    elapsed_ms = (current_ts - last_change_ts) * 1000

    if load_score > 0.7:
        # 부하 높음 → 즉시 감소 (down_ms 대기)
        if elapsed_ms >= down_ms:
            # 20% 감소
            new_pct = max(min_pct, current_pct * 0.8)
            return new_pct, current_ts
        else:
            return current_pct, last_change_ts

    elif load_score < 0.3:
        # 부하 낮음 → 지연 증가 (up_ms 대기)
        if elapsed_ms >= up_ms:
            # 10% 증가
            new_pct = min(max_pct, current_pct * 1.1)
            return new_pct, current_ts
        else:
            return current_pct, last_change_ts

    else:
        # 중간 부하 → 유지
        return current_pct, last_change_ts
