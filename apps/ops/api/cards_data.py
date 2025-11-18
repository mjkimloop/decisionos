from __future__ import annotations

import datetime as dt
import json
import math
import os
import time
from collections import Counter, defaultdict
from typing import Any, Dict, Optional

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


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
    slot = int(math.floor((now - ts) / 86400.0))
    return f"d-{slot}"


def _load_index(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"generated_at": None, "buckets": []}
    except Exception:
        return {"generated_at": None, "buckets": []}


def _load_weights(weights_path: str) -> Dict[str, Any]:
    if not weights_path:
        return {}
    try:
        if yaml:
            with open(weights_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        with open(weights_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def compute_reason_trends(
    period: str = "7d",
    bucket: str = "day",
    top_n: int = 5,
    weights: Optional[Dict[str, Any]] = None,
    index_path: Optional[str] = None,
) -> Dict[str, Any]:
    index_path = index_path or os.getenv("DECISIONOS_EVIDENCE_INDEX", "var/evidence/index.json")
    weights_path = os.getenv("DECISIONOS_CARDS_WEIGHTS", "configs/cards/weights.yaml")
    weight_spec = weights if weights is not None else _load_weights(weights_path)
    data = _load_index(index_path)
    now = time.time()
    if period.endswith("d"):
        period_sec = int(period[:-1]) * 86400
    elif period.endswith("h"):
        period_sec = int(period[:-1]) * 3600
    else:
        period_sec = 7 * 86400

    buckets_src = data.get("buckets") or []
    # 구형 스키마(items)도 방어적으로 처리
    if not buckets_src and data.get("items"):
        buckets_src = [{"ts": it.get("ts"), "reasons": {it.get("reason", "unknown"): 1}} for it in data.get("items", [])]

    group_weights = {k: float(v.get("weight", 1.0)) for k, v in (weight_spec.get("groups") or {}).items()}
    label_weights = {k: float(v.get("weight", 1.0)) for k, v in (weight_spec.get("labels") or {}).items()}
    group_map = weight_spec.get("group_map") or {}

    def _label_group(label: str) -> str:
        for g, labels in group_map.items():
            if label in labels:
                return g
        return (weight_spec.get("labels", {}).get(label, {}) or {}).get("group") or "other"

    groups = defaultdict(lambda: {"score": 0.0, "count": 0, "weight": 1.0})
    buckets_out = []
    reason_scores = defaultdict(float)
    reason_counts = Counter()

    for bucket_entry in buckets_src:
        ts_raw = bucket_entry.get("ts", "")
        ts = _parse_ts(ts_raw)
        if ts and ts < now - period_sec:
            continue
        reasons = bucket_entry.get("reasons") or {}
        bucket_groups = defaultdict(lambda: {"score": 0.0, "count": 0})
        for label, count in reasons.items():
            lbl = str(label)
            cnt = float(count or 0)
            grp = _label_group(lbl)
            l_w = label_weights.get(lbl, 1.0)
            g_w = group_weights.get(grp, 1.0)
            score = cnt * l_w * g_w
            bucket_groups[grp]["score"] += score
            bucket_groups[grp]["count"] += cnt
            groups[grp]["score"] += score
            groups[grp]["count"] += cnt
            groups[grp]["weight"] = g_w
            reason_scores[lbl] += score
            reason_counts[lbl] += cnt
        buckets_out.append(
            {
                "ts": ts_raw,
                "bucket": _bucketize(ts, now, period_sec, "hour" if bucket == "hour" else "day"),
                "groups": dict(bucket_groups),
            }
        )

    top = sorted(reason_scores.items(), key=lambda kv: kv[1], reverse=True)[: max(1, int(top_n))]

    return {
        "generated_at": data.get("generated_at"),
        "period": period,
        "bucket": bucket,
        "groups": dict(groups),
        "buckets": buckets_out,
        "top_reasons": [{"reason": r, "score": s, "count": reason_counts[r]} for r, s in top],
        "summary": {"total_events": sum(reason_counts.values()), "unique_reasons": len(reason_counts)},
        "_meta": {"index_path": index_path, "weights_path": weights_path},
    }


def aggregate(period: str = "7d", bucket: str = "day", top_n: int = 5, index_path: Optional[str] = None) -> Dict[str, Any]:
    return compute_reason_trends(period=period, bucket=bucket, top_n=top_n, index_path=index_path)
