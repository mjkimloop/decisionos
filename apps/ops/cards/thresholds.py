"""
Ops Cards 상한선 관리 (v0.5.11r-9)

SLO에서 정의된 latency/cost 상한선을 Cards API에 통합
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def load_slo_thresholds(slo_path: str | None = None) -> Dict[str, Any]:
    """
    SLO 파일에서 상한선 추출

    Returns:
        {
            "max_latency_ms": int,
            "baseline_latency_ms": int,
            "max_cost_usd": float,
            "max_error_rate": float
        }
    """
    if not slo_path:
        slo_path = os.environ.get(
            "DECISIONOS_SLO_PATH",
            "configs/slo/slo-billing-baseline-v2.json"
        )

    path = Path(slo_path)
    if not path.exists():
        return {}

    try:
        slo = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    thresholds = {}

    # Latency 상한선
    latency = slo.get("latency", {})
    if "max_p95_ms" in latency:
        thresholds["max_latency_ms"] = latency["max_p95_ms"]
    if "baseline_p95_ms" in latency:
        thresholds["baseline_latency_ms"] = latency["baseline_p95_ms"]

    # Cost 상한선
    budget = slo.get("budget", {})
    if "max_spent" in budget:
        thresholds["max_cost_usd"] = budget["max_spent"]

    # Error rate 상한선
    error = slo.get("error", {})
    if "max_error_rate" in error:
        thresholds["max_error_rate"] = error["max_error_rate"]

    return thresholds


def check_threshold_exceeded(current: float, max_threshold: float) -> bool:
    """상한선 초과 여부"""
    return current > max_threshold


def format_threshold_status(current: float, max_threshold: float, baseline: float | None = None) -> Dict[str, Any]:
    """
    상한선 상태 포맷

    Returns:
        {
            "current": float,
            "max": float,
            "baseline": float | None,
            "exceeded": bool,
            "utilization_pct": float
        }
    """
    exceeded = check_threshold_exceeded(current, max_threshold)
    utilization = (current / max_threshold * 100) if max_threshold > 0 else 0.0

    return {
        "current": current,
        "max": max_threshold,
        "baseline": baseline,
        "exceeded": exceeded,
        "utilization_pct": round(utilization, 2),
    }


__all__ = [
    "load_slo_thresholds",
    "check_threshold_exceeded",
    "format_threshold_status",
]
