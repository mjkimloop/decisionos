from __future__ import annotations
import json, os
from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime

SEASONAL_PATH = os.environ.get("CARDS_THRESHOLDS_SEASONAL_PATH", "var/cards/thresholds_seasonal.json")

@dataclass
class GroupStat:
    mean: float
    std: float

@dataclass
class SeasonalThresholds:
    bucket: str  # "hour"|"day"
    by_hour: Dict[str, Dict[str, GroupStat]]  # "00".."23" -> group->stat
    by_dow:  Dict[str, Dict[str, GroupStat]]  # "0".."6"  -> group->stat

def _to_gs(d): return {g: GroupStat(**v) for g, v in d.items()}

def load_seasonal(path: str = SEASONAL_PATH) -> Optional[SeasonalThresholds]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        o = json.load(f)
    by_hour = {k: _to_gs(v) for k, v in o.get("by_hour", {}).items()}
    by_dow  = {k: _to_gs(v) for k, v in o.get("by_dow", {}).items()}
    return SeasonalThresholds(bucket=o.get("bucket", "hour"), by_hour=by_hour, by_dow=by_dow)

def resolve_for(ts: datetime, seasonality: str, st: Optional[SeasonalThresholds]) -> Optional[Dict[str, GroupStat]]:
    if not st or seasonality == "off":
        return None
    if seasonality == "auto":
        key = f"{ts.hour:02d}" if st.bucket == "hour" else str(ts.weekday())
        table = st.by_hour if st.bucket == "hour" else st.by_dow
        return table.get(key)
    if seasonality == "hour":
        return st.by_hour.get(f"{ts.hour:02d}") if st.by_hour else None
    if seasonality == "dow":
        return st.by_dow.get(str(ts.weekday())) if st.by_dow else None
    return None

def dump_example(path: str = SEASONAL_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"bucket": "hour", "by_hour": {}, "by_dow": {}}, f)
