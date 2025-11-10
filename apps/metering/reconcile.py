from __future__ import annotations
import datetime as dt
from collections import defaultdict
from typing import Iterable, Dict, Tuple
from .schema import MeterEvent, MeterBucket, ReconcileReport, ReconcileReportV2, ReconcileCounters
from .ingest import filter_idempotent
from .watermark import WatermarkPolicy

def _floor_hour(ts: dt.datetime) -> dt.datetime:
    return ts.replace(minute=0, second=0, microsecond=0, tzinfo=ts.tzinfo)

def _hour_window(ts: dt.datetime) -> Tuple[dt.datetime, dt.datetime]:
    start = _floor_hour(ts)
    return start, start + dt.timedelta(hours=1)

def aggregate_hourly(events: Iterable[MeterEvent]) -> ReconcileReport:
    uniq, dup = filter_idempotent(events)
    agg: Dict[str, dict] = defaultdict(lambda: {"count": 0, "sum": 0.0, "min": None, "max": None, "ws": None, "we": None, "tenant": "", "metric": ""})

    for ev in uniq:
        ws, we = _hour_window(ev.ts)
        key = f"{ev.tenant}|{ev.metric}|{ws.isoformat()}"
        slot = agg[key]
        slot["tenant"] = ev.tenant
        slot["metric"] = ev.metric
        slot["ws"], slot["we"] = ws, we
        slot["count"] += 1
        slot["sum"] += ev.value
        slot["min"] = ev.value if slot["min"] is None else min(slot["min"], ev.value)
        slot["max"] = ev.value if slot["max"] is None else max(slot["max"], ev.value)

    buckets: Dict[str, MeterBucket] = {}
    for k, v in agg.items():
        buckets[k] = MeterBucket(
            tenant=v["tenant"],
            metric=v["metric"],
            window_start=v["ws"],
            window_end=v["we"],
            count=v["count"],
            sum=round(v["sum"], 6),
            min=v["min"],
            max=v["max"],
        )
    return ReconcileReport(buckets=buckets, duplicates=dup)

# ✅ 워터마크/지연 처리 버전
def aggregate_hourly_with_watermark(
    events: Iterable[MeterEvent],
    now: dt.datetime,
    policy: WatermarkPolicy
) -> ReconcileReportV2:
    uniq, dup = filter_idempotent(events)
    counters = ReconcileCounters(duplicates=dup, late_kept=0, late_dropped=0)
    agg: Dict[str, dict] = defaultdict(lambda: {"count": 0, "sum": 0.0, "min": None, "max": None, "ws": None, "we": None, "tenant": "", "metric": ""})

    for ev in uniq:
        cls = policy.classify(ev.ts, now)
        if cls == "late_dropped" and policy.drop_too_late:
            counters.late_dropped += 1
            continue
        if cls == "late_kept":
            counters.late_kept += 1

        ws, we = _hour_window(ev.ts)  # ※ 항상 이벤트 타임스탬프 기준 윈도
        key = f"{ev.tenant}|{ev.metric}|{ws.isoformat()}"
        s = agg[key]
        s["tenant"] = ev.tenant; s["metric"] = ev.metric
        s["ws"], s["we"] = ws, we
        s["count"] += 1
        s["sum"] += ev.value
        s["min"] = ev.value if s["min"] is None else min(s["min"], ev.value)
        s["max"] = ev.value if s["max"] is None else max(s["max"], ev.value)

    buckets: Dict[str, MeterBucket] = {}
    for k, v in agg.items():
        buckets[k] = MeterBucket(
            tenant=v["tenant"], metric=v["metric"],
            window_start=v["ws"], window_end=v["we"],
            count=v["count"], sum=round(v["sum"], 6), min=v["min"], max=v["max"]
        )
    return ReconcileReportV2(buckets=buckets, counters=counters)
