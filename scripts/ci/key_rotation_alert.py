#!/usr/bin/env python3
"""Key rotation alert for signed-policy infrastructure.

Detects:
- Active keys expiring soon (within ROTATION_SOON_DAYS)
- Insufficient overlap between active/grace keys (< GRACE_OVERLAP_DAYS)

Outputs JSON report for CI integration (check runs, PR comments).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from typing import Any, Dict, List

# 키 포맷 예시:
# DECISIONOS_POLICY_KEYS='[{"key_id":"k1","secret":"...","state":"active","not_before":"2025-10-01T00:00:00Z","not_after":"2026-01-01T00:00:00Z"}, ...]'

ISO = "%Y-%m-%dT%H:%M:%SZ"


def _parse_keys(env=os.environ) -> List[Dict[str, Any]]:
    """Parse keys from environment variable (JSON array)."""
    raw = env.get("DECISIONOS_POLICY_KEYS") or env.get("DECISIONOS_JUDGE_KEYS") or "[]"
    try:
        keys = json.loads(raw)
    except Exception as e:
        raise SystemExit(f"FAIL: invalid keys JSON: {e}")

    # 정규화: datetime 객체로 변환
    out = []
    for k in keys:
        nb = k.get("not_before")
        na = k.get("not_after")
        k["not_before_dt"] = dt.datetime.strptime(nb, ISO) if nb else None
        k["not_after_dt"] = dt.datetime.strptime(na, ISO) if na else None
        out.append(k)
    return out


def _days_left(d: dt.datetime) -> float:
    """Calculate days remaining until given datetime."""
    now = dt.datetime.utcnow()
    return (d - now).total_seconds() / 86400.0


def _overlap_days(a_start, a_end, b_start, b_end) -> float:
    """Calculate overlap in days between two time ranges."""
    if not a_start or not a_end or not b_start or not b_end:
        return 0.0
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    delta = (end - start).total_seconds() / 86400.0
    return max(0.0, delta)


def analyze(keys: List[Dict[str, Any]], soon_days: int, min_overlap: int) -> Dict[str, Any]:
    """Analyze key rotation status and return findings."""
    report = {
        "now": dt.datetime.utcnow().strftime(ISO),
        "soon_days": soon_days,
        "min_overlap_days": min_overlap,
        "findings": [],
        "summary": {"status": "ok", "warnings": 0, "errors": 0},
    }

    # active/grace 키 분류
    actives = [k for k in keys if k.get("state") in ("active", "grace")]

    # 1) active 키 만료 임박 체크
    for k in actives:
        na = k.get("not_after_dt")
        if na:
            days = _days_left(na)
            if days <= soon_days:
                report["findings"].append(
                    {"code": "key.expiry_soon", "key_id": k.get("key_id"), "days_left": round(days, 2)}
                )

    # 2) 겹침 보장: active 키들 간의 overlap 체크
    for i, a in enumerate(actives):
        for b in actives[i + 1 :]:
            ov = _overlap_days(a["not_before_dt"], a["not_after_dt"], b["not_before_dt"], b["not_after_dt"])
            if ov < min_overlap:
                report["findings"].append(
                    {
                        "code": "key.overlap_insufficient",
                        "a": a.get("key_id"),
                        "b": b.get("key_id"),
                        "overlap_days": round(ov, 2),
                    }
                )

    # 요약
    for f in report["findings"]:
        if f["code"].startswith("key.overlap"):
            report["summary"]["warnings"] += 1
        elif f["code"].startswith("key.expiry"):
            report["summary"]["warnings"] += 1

    if report["summary"]["warnings"] > 0:
        report["summary"]["status"] = "warn"

    return report


def main():
    """Main entry point for key rotation alert."""
    soon_days = int(os.environ.get("ROTATION_SOON_DAYS", "14"))
    min_overlap = int(os.environ.get("GRACE_OVERLAP_DAYS", "7"))

    keys = _parse_keys()
    rep = analyze(keys, soon_days, min_overlap)

    print(json.dumps(rep, ensure_ascii=False, indent=2))

    # 종료코드: warn=8, ok=0 (치명 조건은 여기선 경고로 처리)
    sys.exit(8 if rep["summary"]["status"] == "warn" else 0)


if __name__ == "__main__":
    main()
