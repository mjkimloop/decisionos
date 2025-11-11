#!/usr/bin/env python3
"""
Autotune: calibrated Δ 기반 자동 승격 임계 재조정
- robust_scale (MAD), suggest_thresholds (delta_threshold, p_win_threshold, min_windows)
"""
import math

def robust_scale(values, factor=1.4826):
    """MAD(Median Absolute Deviation) 기반 robust scale"""
    if not values:
        return 0.0
    median = sorted(values)[len(values) // 2]
    deviations = [abs(v - median) for v in values]
    mad = sorted(deviations)[len(deviations) // 2]
    return mad * factor

def suggest_thresholds(ab_reports, calibration_gain=1.0, safety_factor=2.0):
    """
    교정된 Δ 기반 자동 임계 조정
    Args:
        ab_reports: list of {delta: {mean, ci95_low, ci95_high}, p_win, ...}
        calibration_gain: 교정 게인
        safety_factor: 안전 계수 (default 2.0)
    Returns:
        {delta_threshold, p_win_threshold, min_windows, obs_variance}
    """
    if not ab_reports:
        return {
            "delta_threshold": 0.0,
            "p_win_threshold": 0.5,
            "min_windows": 3,
            "obs_variance": 0.0,
            "method": "empty"
        }

    deltas = []
    p_wins = []
    for r in ab_reports:
        delta = r.get("delta", {})
        mean = delta.get("mean", 0.0)
        deltas.append(mean * calibration_gain)
        p_wins.append(r.get("p_win", 0.5))

    # robust scale for variance
    obs_var = robust_scale(deltas)

    # delta_threshold: safety_factor * obs_variance
    delta_threshold = safety_factor * obs_var

    # p_win_threshold: median + 0.1
    p_win_sorted = sorted(p_wins)
    p_win_median = p_win_sorted[len(p_win_sorted) // 2]
    p_win_threshold = min(0.95, p_win_median + 0.1)

    # min_windows: max(3, len(ab_reports) // 2)
    min_windows = max(3, len(ab_reports) // 2)

    return {
        "delta_threshold": round(delta_threshold, 4),
        "p_win_threshold": round(p_win_threshold, 4),
        "min_windows": min_windows,
        "obs_variance": round(obs_var, 4),
        "method": "robust_mad"
    }
