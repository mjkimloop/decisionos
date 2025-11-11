from __future__ import annotations
from typing import List, Dict, Any
import math

def compute_gain(pred: List[float], obs: List[float], eps: float = 1e-9) -> Dict[str, Any]:
    """
    예측 델타(pred)와 실측 델타(obs)를 정렬된 동일 길이로 받은 뒤
    원점 통과 최소제곱(slope)과 평균비(mean-ratio)를 함께 계산.
    """
    n = min(len(pred), len(obs))
    p = pred[:n]
    o = obs[:n]
    if n == 0:
        return {"gain": 1.0, "method": "identity", "samples": 0}
    num = sum(oi * pi for oi, pi in zip(o, p))
    den = sum(pi * pi for pi in p) + eps
    slope = num / den
    mean_ratio = (sum(o) / (sum(p) + eps)) if abs(sum(p)) > eps else 1.0
    # 안정성: 극단값 방지 클리핑
    gain = max(0.1, min(10.0, 0.5 * slope + 0.5 * mean_ratio))
    return {
        "gain": gain,
        "method": "avg(slope,mean_ratio)",
        "samples": n,
        "slope": slope,
        "mean_ratio": mean_ratio
    }

def apply_calibration_to_ab_report(ab: Dict[str, Any], gain: float) -> Dict[str, Any]:
    out = dict(ab)
    d = dict(out.get("delta", {}))
    # mean/ci/risk 스케일; p_win은 그대로 두고, 보정 p_win도 별도 필드 제공 가능
    if "mean" in d:
        d["mean"] = d["mean"] * gain
    if "ci95_low" in d:
        d["ci95_low"] = d["ci95_low"] * gain
    if "ci95_high" in d:
        d["ci95_high"] = d["ci95_high"] * gain
    if "objective" in d:
        d["objective"] = d["objective"] * gain  # 비부트스트랩 경로
    if "risk" in d:
        d["risk"] = abs(d.get("mean", d.get("objective", 0.0))) * (d.get("risk_factor", 1.0))
    d["calibrated_gain"] = gain
    out["delta"] = d
    return out
