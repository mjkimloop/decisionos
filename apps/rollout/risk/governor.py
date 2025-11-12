"""
Risk Governor
다중 신호 융합을 통한 risk_score 계산 및 배포 정책 결정
"""
import json
import os
from typing import Dict, Any, Optional


def load_governor_config(path: str = "configs/rollout/risk_governor.json") -> Dict[str, Any]:
    """Governor 설정 로드"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Governor config not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_signal(value: Any, norm_spec: Dict[str, Any]) -> float:
    """
    신호 정규화 (0.0 ~ 1.0 범위로)

    지원 타입:
    - zscore: z-score 기반, cap으로 상한
    - linear: 이미 0~1 범위
    - minmax: min~max 구간을 0~1로 매핑
    - enum: 맵 기반 고정 값
    """
    norm_type = norm_spec.get("type", "linear")

    if norm_type == "zscore":
        # z-score는 이미 정규화된 값으로 가정
        cap = norm_spec.get("cap", 5.0)
        z = float(value)
        # -cap ~ +cap를 0~1로 매핑
        normalized = (z + cap) / (2 * cap)
        return max(0.0, min(1.0, normalized))

    elif norm_type == "linear":
        # 이미 0~1 범위
        v = float(value)
        return max(0.0, min(1.0, v))

    elif norm_type == "minmax":
        # min~max 구간을 0~1로 매핑
        v = float(value)
        vmin = float(norm_spec.get("min", 0))
        vmax = float(norm_spec.get("max", 1))

        if vmax == vmin:
            return 0.0

        normalized = (v - vmin) / (vmax - vmin)
        return max(0.0, min(1.0, normalized))

    elif norm_type == "enum":
        # 맵 기반 고정 값
        mapping = norm_spec.get("map", {})
        str_value = str(value).lower()
        return float(mapping.get(str_value, 0.0))

    else:
        # 기본값
        return 0.0


def compute_risk_score(signals: Dict[str, Any], config: Dict[str, Any]) -> float:
    """
    가중 합산으로 risk_score 계산

    Args:
        signals: 입력 신호 딕셔너리
        config: governor 설정 (weights, norm 포함)

    Returns:
        risk_score (0.0 이상, 일반적으로 0~1 범위이나 초과 가능)
    """
    weights = config.get("weights", {})
    norms = config.get("norm", {})

    risk_score = 0.0

    for signal_name, weight in weights.items():
        if signal_name not in signals:
            # 신호 누락 시 0으로 처리 (또는 기본값)
            continue

        raw_value = signals[signal_name]
        norm_spec = norms.get(signal_name, {"type": "linear"})

        normalized = normalize_signal(raw_value, norm_spec)
        risk_score += weight * normalized

    return risk_score


def get_action(risk_score: float, mapping: list) -> Dict[str, Any]:
    """
    맵핑 테이블에서 risk_score에 해당하는 액션 결정

    Args:
        risk_score: 계산된 리스크 점수
        mapping: range와 action으로 구성된 맵핑 테이블

    Returns:
        action 딕셔너리 (mode, step_inc, cap 등)
    """
    for entry in mapping:
        range_min, range_max = entry["range"]
        if range_min <= risk_score < range_max:
            return entry["action"]

    # 범위를 벗어나면 마지막 항목 또는 기본값
    if mapping:
        return mapping[-1]["action"]

    return {"mode": "freeze", "step_inc": 0, "cap": 0}
