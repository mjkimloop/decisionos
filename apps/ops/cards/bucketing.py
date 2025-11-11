from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Callable
from collections import defaultdict

def _floor_hour(dt: datetime) -> datetime:
    return dt.replace(minute=0, second=0, microsecond=0)

def _floor_day(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)

def bucketize_counts_by_time(
    rows: List[Dict[str, Any]],  # [{"ts": ISO8601, "reason": str}, ...]
    bucket_size: str,  # "hour" | "day"
) -> List[Dict[str, Any]]:
    """
    Bucketize reason events by time window.
    Returns: [{start, end, total, raw: {reason: count}}]
    """
    floor = _floor_hour if bucket_size == "hour" else _floor_day
    delta = timedelta(hours=1) if bucket_size == "hour" else timedelta(days=1)

    buckets: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        ts_str = row.get("ts", "")
        if ts_str.endswith("Z"):
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        else:
            ts = datetime.fromisoformat(ts_str)
        if not ts.tzinfo:
            ts = ts.replace(tzinfo=timezone.utc)

        bucket_start = floor(ts)
        bucket_end = bucket_start + delta
        key = bucket_start.isoformat()

        if key not in buckets:
            buckets[key] = {
                "start": bucket_start.isoformat(),
                "end": bucket_end.isoformat(),
                "total": 0,
                "raw": defaultdict(int),
            }
        buckets[key]["total"] += 1
        buckets[key]["raw"][row.get("reason", "unknown")] += 1

    # Convert defaultdict to dict and sort by start time
    result = []
    for b in sorted(buckets.values(), key=lambda x: x["start"]):
        b["raw"] = dict(b["raw"])
        result.append(b)
    return result

def apply_bucket_scores(
    buckets: List[Dict[str, Any]],
    group_of: Callable[[str], str],
    weights: Dict[str, float],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for b in buckets:
        raw: Dict[str, int] = b.get("raw", {})
        score = 0.0
        for label, cnt in raw.items():
            g = group_of(label)
            w = weights.get(g, 1.0)
            score += float(cnt) * w
        nb = dict(b)
        nb["score"] = round(score, 6)
        out.append(nb)
    return out

def pick_top_buckets(buckets_scored: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    k = max(1, min(k, len(buckets_scored)))
    ranked = sorted(buckets_scored, key=lambda x: x.get("score", 0.0), reverse=True)
    # 상위 버킷은 핵심 정보만 요약
    res: List[Dict[str, Any]] = []
    for b in ranked[:k]:
        raw = b.get("raw", {})
        # 버킷 내 상위 라벨 3개
        top_reasons = sorted(raw.items(), key=lambda x: x[1], reverse=True)[:3]
        res.append({
            "start": b["start"], "end": b["end"],
            "score": b.get("score", 0.0),
            "total": b.get("total", 0),
            "top_reasons": [{"label": r, "count": c} for (r, c) in top_reasons],
        })
    return res
