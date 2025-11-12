from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Dict

@dataclass
class BurnRateConfig:
    target_availability: float = 0.995
    window_sec: int = 3600
    thresholds: Dict[str, float] = None  # {"warn": 1.0, "critical": 2.0}

def compute_burn_rate(total_requests: int, error_requests: int, cfg: BurnRateConfig) -> float:
    """
    Burn rate = actual_error_rate / expected_error_rate
    If burn_rate > 1.0, we're consuming error budget faster than expected
    """
    if total_requests <= 0:
        return 0.0
    actual_error_rate = error_requests / total_requests
    expected_error_rate = 1.0 - cfg.target_availability  # error budget per request
    if expected_error_rate <= 0:
        return 0.0
    return actual_error_rate / expected_error_rate

def evaluate_burn_rate(br: float, cfg: BurnRateConfig) -> Literal["ok", "warn", "critical"]:
    thr = cfg.thresholds or {"warn": 1.0, "critical": 2.0}
    if br >= float(thr.get("critical", 2.0)):
        return "critical"
    if br >= float(thr.get("warn", 1.0)):
        return "warn"
    return "ok"
