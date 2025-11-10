from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Dict, Optional
import hashlib
import datetime as dt

class MeterEvent(BaseModel):
    tenant: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    corr_id: str = Field(min_length=1)  # idempotency correlation id
    ts: dt.datetime
    value: float = Field(ge=0.0)
    tags: Dict[str, str] = {}

    def idempotency_key(self) -> str:
        raw = f"{self.tenant}|{self.metric}|{self.corr_id}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

class MeterBucket(BaseModel):
    tenant: str
    metric: str
    window_start: dt.datetime
    window_end: dt.datetime
    count: int
    sum: float
    min: float
    max: float

class ReconcileReport(BaseModel):
    buckets: Dict[str, MeterBucket]  # key = f"{tenant}|{metric}|{window_start.isoformat()}"
    duplicates: int = 0

# ✅ V2: 지연/드롭 카운터 포함
class ReconcileCounters(BaseModel):
    duplicates: int = 0
    late_kept: int = 0
    late_dropped: int = 0

class ReconcileReportV2(BaseModel):
    buckets: Dict[str, MeterBucket]
    counters: ReconcileCounters = ReconcileCounters()