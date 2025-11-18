from __future__ import annotations

import datetime as dt
import json
import math
import os
import time
from collections import Counter, defaultdict
from typing import Any, Dict, Optional


def _parse_ts(ts: str) -> float:
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return dt.datetime.fromisoformat(ts).timestamp()
    except Exception:
        return 0.0


def _bucketize(ts: float, now: float, period_sec: int, bucket: str) -> str:
    if bucket == "hour":
        slot = int(math.floor((now - ts) / 3600.0))
        return f"h-{slot}"
    else:
        slot = int(math.floor((now - ts) / 86400.0))
        return f"d-{slot}"


def _load_index(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_reason_trends(
    period: str = "7d",
    bucket: str = "day",
    top_n: int = 5,
    weight_map: Optional[Dict[str, float]] = None,
    index_path: Optional[str] = None,
) -> Dict[str, Any]:
    index_path = index_path or os.getenv("DECISIONOS_EVIDENCE_INDEX", "var/evidence/index.json")
    data = _load_index(index_path)
    now = time.time()
    if period.endswith("d"):
        period_sec = int(period[:-1]) * 86400
    elif period.endswith("h"):
        period_sec = int(period[:-1]) * 3600
    else:
        period_sec = 7 * 86400

    items = data.get("items", []) if isinstance(data, dict) else []
    w = defaultdict(float)
    by_bucket = defaultdict(lambda: defaultdict(float))
    counts = Counter()

    for it in items:
        ts = _parse_ts(it.get("ts", ""))
        if ts < now - period_sec:
            continue
        reason = it.get("reason") or "unknown"
        base_weight = float(it.get("weight", 1.0))
        extra = (weight_map or {}).get(reason, 1.0)
        weight = base_weight * float(extra)

        bkey = _bucketize(ts, now, period_sec, "hour" if bucket == "hour" else "day")
        by_bucket[bkey][reason] += weight
        w[reason] += weight
        counts[reason] += 1

    top = sorted(w.items(), key=lambda kv: kv[1], reverse=True)[: max(1, int(top_n))]
    series = []
    for bkey in sorted(by_bucket.keys(), key=lambda k: int(k.split("-")[1])):
        series.append(
            {"bucket": bkey, "reasons": dict(sorted(by_bucket[bkey].items(), key=lambda kv: kv[1], reverse=True))}
        )

    return {
        "generated_at": data.get("generated_at"),
        "period": period,
        "bucket": bucket,
        "top_reasons": [{"reason": r, "score": s, "count": counts[r]} for r, s in top],
        "series": series,
        "summary": {"total_events": sum(counts.values()), "unique_reasons": len(counts)},
        "_meta": {"index_path": index_path},
    }


def aggregate(period: str = "7d", bucket: str = "day", top_n: int = 5, index_path: Optional[str] = None) -> Dict[str, Any]:
    return compute_reason_trends(period=period, bucket=bucket, top_n=top_n, index_path=index_path)
