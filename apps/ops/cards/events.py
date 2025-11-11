from __future__ import annotations
import os, json
from typing import Iterable, Dict, Any, List
from datetime import datetime, timezone

EV_PATH = os.environ.get("REASON_EVENTS_PATH", "var/evidence/reasons.jsonl")

def _parse_ts(s: str) -> datetime:
    # ISO8601 지원(Z 포함). tz 미지정 시 UTC 가정.
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        return datetime.fromisoformat(s)
    except Exception:
        # 관대한 파서: 실패 시 UTC naive → aware
        dt = datetime.fromisoformat(s.split(".")[0])
        return dt.replace(tzinfo=timezone.utc)

def load_reason_events(start: datetime, end: datetime, path: str = EV_PATH) -> List[str]:
    reasons: List[str] = []
    if not os.path.exists(path):
        return reasons
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            ts = _parse_ts(obj["ts"])
            if ts >= start and ts < end:
                reasons.append(obj["reason"])
    return reasons
