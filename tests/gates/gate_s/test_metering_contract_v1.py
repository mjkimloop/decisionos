import datetime as dt
import pytest

pytestmark = [pytest.mark.gate_s]

from apps.metering.schema import MeterEvent
from apps.metering.reconcile import aggregate_hourly

def _ev(tenant, metric, corr, ts, value):
    return MeterEvent(tenant=tenant, metric=metric, corr_id=corr, ts=ts, value=value)

def test_metering_contract_v1_idempotency_and_hour_aggregate():
    base = dt.datetime(2025, 1, 1, 10, 15, 0)

    evts = [
        _ev("t1", "tokens", "c1", base, 10.0),
        _ev("t1", "tokens", "c1", base, 10.0),  # duplicate corr_id
        _ev("t1", "tokens", "c2", base, 5.0),
        _ev("t1", "tokens", "c3", base + dt.timedelta(minutes=30), 7.0),
        _ev("t1", "tokens", "c4", base + dt.timedelta(hours=1, minutes=1), 3.0),  # next hour
    ]

    rep = aggregate_hourly(evts)
    # 중복 1건 필터
    assert rep.duplicates == 1

    keys = sorted(rep.buckets.keys())
    # 두 개의 시간창이 생겨야 함
    assert len(keys) == 2

    # 첫 시간창 집계 확인
    first_key = keys[0]
    b0 = rep.buckets[first_key]
    assert b0.count == 3   # c1,c2,c3 (dup 제거됨)
    assert abs(b0.sum - 22.0) < 1e-6
    assert b0.min == 5.0 and b0.max == 10.0

    # 두 번째 시간창 집계 확인
    second_key = keys[1]
    b1 = rep.buckets[second_key]
    assert b1.count == 1 and abs(b1.sum - 3.0) < 1e-6
