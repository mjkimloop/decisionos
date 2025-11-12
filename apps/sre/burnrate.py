"""
Error Budget Burn Rate
SLO error budget 소모율 계산 및 임계 판정
"""
import json
import os
from typing import Dict, Any, Tuple


def load_burn_rate_config(path: str = "configs/rollout/burn_rate.json") -> Dict[str, Any]:
    """Burn-rate 설정 로드"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Burn-rate config not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_burn_rate(
    errors: int,
    total: int,
    objective: Dict[str, float],
    window_sec: int
) -> float:
    """
    Error budget 소모율 계산

    Args:
        errors: 윈도우 내 에러 수
        total: 윈도우 내 총 요청 수
        objective: SLO 목표 (target_availability)
        window_sec: 윈도우 크기 (초)

    Returns:
        burn_rate: 소모율 (1.0 = 정상 소모율, >1.0 = 초과 소모)
    """
    if total == 0:
        return 0.0

    target_availability = objective.get("target_availability", 0.995)
    error_budget = 1.0 - target_availability  # 예: 0.005 (0.5%)

    actual_error_rate = errors / total
    expected_error_rate = error_budget

    if expected_error_rate == 0:
        # error budget이 0이면 어떤 에러도 허용 안됨
        return float("inf") if errors > 0 else 0.0

    burn_rate = actual_error_rate / expected_error_rate
    return burn_rate


def check_threshold(burn_rate: float, thresholds: Dict[str, float]) -> str:
    """
    Burn-rate 임계 판정

    Args:
        burn_rate: 계산된 소모율
        thresholds: 임계값 딕셔너리 (warn, critical)

    Returns:
        레벨 문자열: "ok", "warn", "critical"
    """
    critical_threshold = thresholds.get("critical", 2.0)
    warn_threshold = thresholds.get("warn", 1.0)

    if burn_rate >= critical_threshold:
        return "critical"
    elif burn_rate >= warn_threshold:
        return "warn"
    else:
        return "ok"
