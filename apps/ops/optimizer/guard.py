#!/usr/bin/env python3
"""
Autotune Guard: bounds/slew_rate/rollback 안전장치
"""
from __future__ import annotations
from typing import Dict

def clamp(v: float, lo: float, hi: float) -> float:
    """값을 범위 내로 제한"""
    return max(lo, min(hi, v))

def apply_bounds_slew(
    proposed: Dict[str, float],
    base: Dict[str, float],
    bounds: Dict[str, float],
    slew: Dict[str, float]
) -> Dict[str, float]:
    """
    제안된 값에 bounds와 slew_rate 적용
    Args:
        proposed: 제안된 임계값 {delta_threshold, p_win_threshold, min_windows}
        base: 현재/기준 값
        bounds: 절대 범위 제한
        slew: 단계별 최대 변화량
    Returns:
        안전장치 적용된 값
    """
    out = dict(proposed)

    # Bounds 적용
    out["delta_threshold"] = clamp(
        out.get("delta_threshold", 0.0),
        bounds.get("delta_threshold_min", 0.01),
        bounds.get("delta_threshold_max", 0.15)
    )
    out["p_win_threshold"] = clamp(
        out.get("p_win_threshold", 0.5),
        bounds.get("p_win_threshold_min", 0.55),
        bounds.get("p_win_threshold_max", 0.80)
    )
    mw = int(round(clamp(
        out.get("min_windows", 3),
        bounds.get("min_windows_min", 3),
        bounds.get("min_windows_max", 15)
    )))
    out["min_windows"] = mw

    # Slew-rate 적용 (절대 변화량 제한)
    for k in ("delta_threshold", "p_win_threshold"):
        base_val = base.get(k, out[k])
        dv = out[k] - base_val
        cap = abs(slew.get(k, abs(dv)))
        if abs(dv) > cap:
            out[k] = base_val + (cap if dv > 0 else -cap)

    # min_windows slew-rate
    base_mw = int(base.get("min_windows", out["min_windows"]))
    mw_diff = out["min_windows"] - base_mw
    mw_cap = int(slew.get("min_windows", 0))
    if mw_cap > 0 and abs(mw_diff) > mw_cap:
        out["min_windows"] = base_mw + (mw_cap if mw_diff > 0 else -mw_cap)

    return out


def apply_bounds_slew_adaptive(
    proposed: Dict[str, float],
    base: Dict[str, float],
    bounds: Dict[str, float],
    adaptive_caps: Dict[str, float]
) -> Dict[str, float]:
    """
    제안된 값에 bounds와 adaptive slew_rate 적용

    Args:
        proposed: 제안된 임계값 {delta_threshold, p_win_threshold, min_windows}
        base: 현재/기준 값
        bounds: 절대 범위 제한
        adaptive_caps: 적응형 동적 cap (adaptive.py의 compute_adaptive_caps 결과)
    Returns:
        안전장치 적용된 값
    """
    # adaptive_caps를 slew로 사용하여 기존 로직 재활용
    return apply_bounds_slew(proposed, base, bounds, adaptive_caps)


def should_rollback(
    drift_json: dict,
    trigger: dict,
    consec_state_path: str = "var/alerts/_drift_consec.state"
) -> bool:
    """
    롤백 필요 여부 판단
    severity가 trigger 목록에 있고 연속 횟수가 threshold 이상이면 True
    Args:
        drift_json: posterior_drift.json 내용
        trigger: {"severity": ["critical"], "consecutive": 2}
        consec_state_path: 연속 카운터 상태 파일
    Returns:
        롤백 필요 여부
    """
    import os, json

    sev = str(drift_json.get("severity", "info"))
    wanted = set(trigger.get("severity", []))
    need = int(trigger.get("consecutive", 2))

    # 현재 연속 카운터 로드
    cur = 0
    if os.path.exists(consec_state_path):
        try:
            cur = int(json.load(open(consec_state_path, "r", encoding="utf-8")).get("count", 0))
        except Exception:
            cur = 0

    # severity 매칭 시 카운터 증가, 아니면 리셋
    if sev in wanted:
        cur += 1
    else:
        cur = 0

    # 상태 저장
    os.makedirs(os.path.dirname(consec_state_path) if os.path.dirname(consec_state_path) else ".", exist_ok=True)
    json.dump({"count": cur}, open(consec_state_path, "w", encoding="utf-8"))

    return cur >= need
