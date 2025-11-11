"""
Adaptive Slew Limiter
분산·혼잡도 기반 동적 cap 조정
"""
import json
import os
from typing import Dict, Any


def load_adaptive(path: str) -> Dict[str, Any]:
    """adaptive.json 로드"""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_bucket_stats(path: str) -> Dict[str, Any]:
    """bucket_stats.json 로드 (variance, congestion 등)"""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_congestion(stats: Dict[str, Any]) -> float:
    """
    혼잡도 점수 계산
    stats에서 congestion 메트릭을 추출하거나 계산
    """
    # 직접 제공된 congestion 값 사용
    if "congestion" in stats:
        return float(stats["congestion"])

    # 대안: alert_rate나 다른 메트릭에서 유추
    if "alert_rate" in stats:
        alert_rate = float(stats["alert_rate"])
        # 간단한 매핑: alert_rate가 높으면 혼잡도 높음
        return min(alert_rate * 10.0, 1.0)

    # 기본값
    return 0.0


def compute_adaptive_caps(
    base_caps: Dict[str, float],
    stats: Dict[str, Any],
    adaptive_cfg: Dict[str, Any]
) -> Dict[str, float]:
    """
    동적 cap 계산

    Args:
        base_caps: 기본 slew_rate 설정 (예: {"delta_threshold": 0.02, "p_win_threshold": 0.05, ...})
        stats: bucket_stats.json에서 로드한 메트릭 (variance, congestion 등)
        adaptive_cfg: adaptive.json 설정

    Returns:
        조정된 adaptive_caps
    """
    variance = stats.get("variance", 0.0)
    congestion = resolve_congestion(stats)

    variance_scale = adaptive_cfg.get("variance_scale", 2.0)
    congestion_scale = adaptive_cfg.get("congestion_scale", 1.5)
    floors = adaptive_cfg.get("floors", {})
    ceilings = adaptive_cfg.get("ceilings", {})

    adaptive_caps = {}

    for key, base_cap in base_caps.items():
        # 분산·혼잡도 기반 팩터 계산
        variance_factor = 1.0 + (variance * variance_scale)
        congestion_factor = 1.0 + (congestion * congestion_scale)

        # 동적 cap = base_cap * variance_factor * congestion_factor
        cap = base_cap * variance_factor * congestion_factor

        # floor/ceiling 제약 적용
        floor = floors.get(key, 0.0)
        ceiling = ceilings.get(key, float("inf"))

        clamped = max(floor, min(cap, ceiling))

        # min_windows는 정수로 변환
        if key == "min_windows" or key.endswith("_windows"):
            adaptive_caps[key] = int(round(clamped))
        else:
            adaptive_caps[key] = clamped

    return adaptive_caps
