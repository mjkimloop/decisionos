import datetime as dt
import os, json
import pytest

pytestmark = [pytest.mark.gate_s]

from apps.metering.schema import MeterEvent
from apps.metering.ingest import filter_idempotent_with
from apps.metering.store import InMemoryIdempoStore, SQLiteIdempoStore

def _ev(corr: str, ts: dt.datetime, v: float) -> MeterEvent:
    return MeterEvent(tenant="t1", metric="tokens", corr_id=corr, ts=ts, value=v)

def test_inmemory_idempotency_basic():
    store = InMemoryIdempoStore()
    try:
        uniq, dup = filter_idempotent_with(store, [
            _ev("c1", dt.datetime(2025,1,1,0,0,0), 1.0),
            _ev("c1", dt.datetime(2025,1,1,0,0,1), 2.0),  # dup
            _ev("c2", dt.datetime(2025,1,1,0,0,2), 3.0)
        ])
        assert len(uniq) == 2 and dup == 1
    finally:
        store.close()

def test_sqlite_idempotency_persistent(tmp_path):
    db = tmp_path / "idempo.sqlite"
    s1 = SQLiteIdempoStore(str(db))
    s2 = SQLiteIdempoStore(str(db))
    try:
        e1 = _ev("c1", dt.datetime(2025,1,1,0,0,0), 1.0)
        e2 = _ev("c1", dt.datetime(2025,1,1,0,0,1), 2.0)  # dup across another instance
        uniq1, dup1 = filter_idempotent_with(s1, [e1])
        uniq2, dup2 = filter_idempotent_with(s2, [e2])
        assert len(uniq1) == 1 and dup1 == 0
        assert len(uniq2) == 0 and dup2 == 1
    finally:
        s1.close(); s2.close()
