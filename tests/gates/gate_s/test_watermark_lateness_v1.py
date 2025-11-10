import datetime as dt
import pytest

pytestmark = [pytest.mark.gate_s]

from apps.metering.schema import MeterEvent
from apps.metering.reconcile import aggregate_hourly_with_watermark
from apps.metering.watermark import WatermarkPolicy

def _ev(tenant, metric, corr, ts, value):
    return MeterEvent(tenant=tenant, metric=metric, corr_id=corr, ts=ts, value=value)

def test_watermark_lateness_v1_drop_and_keep():
    now = dt.datetime(2025, 1, 1, 10, 40, 0)
    pol = WatermarkPolicy(max_lag_sec=15*60, drop_too_late=True)  # 15분

    evts = [
        _ev("t1", "tokens", "c1", dt.datetime(2025,1,1,10,35,0), 5.0),   # age=5m -> late_kept
        _ev("t1", "tokens", "c2", dt.datetime(2025,1,1,10,10,0), 7.0),   # age=30m -> late_dropped
        _ev("t1", "tokens", "c3", dt.datetime(2025,1,1,10,45,0), 3.0),   # future(−5m) -> on_time
        _ev("t1", "tokens", "c1", dt.datetime(2025,1,1,10,35,1), 9.0),   # duplicate corr_id -> duplicates++
    ]

    rep = aggregate_hourly_with_watermark(evts, now=now, policy=pol)

    # 카운터 검증
    assert rep.counters.late_kept == 1
    assert rep.counters.late_dropped == 1
    assert rep.counters.duplicates == 1

    # 버킷 검증: 10:00~11:00(kept 1 + future 1 = count 2), 11:00~12:00 없음(미래 ev도 10:00 윈도)
    keys = sorted(rep.buckets.keys())
    assert len(keys) == 1
    b = rep.buckets[keys[0]]
    assert b.window_start == dt.datetime(2025,1,1,10,0,0)
    assert b.count == 2
    # sum = 5.0 (late_kept) + 3.0 (future on_time)
    assert abs(b.sum - 8.0) < 1e-6
    assert b.min == 3.0 and b.max == 5.0
