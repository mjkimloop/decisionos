from __future__ import annotations
from pydantic import BaseModel
from typing import Dict, Iterable
from apps.metering.schema import MeterBucket, ReconcileReport, ReconcileReportV2
from .plans import Plan

class LineItem(BaseModel):
    metric: str
    usage: float
    included: float
    overage_units: float
    overage_rate: float
    amount: float

class RatingResult(BaseModel):
    subtotal: float
    items: list[LineItem]

def _sum_usage_by_metric(buckets: Dict[str, MeterBucket]) -> Dict[str, float]:
    agg: Dict[str, float] = {}
    for b in buckets.values():
        agg[b.metric] = agg.get(b.metric, 0.0) + float(b.sum)
    return agg

def rate_from_buckets(plan: Plan, buckets: Dict[str, MeterBucket]) -> RatingResult:
    usage = _sum_usage_by_metric(buckets)
    items: list[LineItem] = []
    subtotal = 0.0
    for metric, used in usage.items():
        mp = plan.metrics.get(metric)
        if not mp:
            # 미정의 metric은 과금 0 (v1 정책)
            items.append(LineItem(metric=metric, usage=used, included=0.0,
                                  overage_units=0.0, overage_rate=0.0, amount=0.0))
            continue
        over = max(0.0, used - mp.included)
        amt = over * mp.overage_rate
        subtotal += amt
        items.append(LineItem(metric=metric, usage=used, included=mp.included,
                              overage_units=over, overage_rate=mp.overage_rate, amount=amt))
    return RatingResult(subtotal=round(subtotal, 6), items=items)

def rate_report(plan: Plan, rep: ReconcileReport | ReconcileReportV2) -> RatingResult:
    # ReconcileReportV2도 buckets 동일 키
    buckets = rep.buckets
    return rate_from_buckets(plan, buckets)
