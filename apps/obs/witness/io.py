"""
apps/obs/witness/io.py

Witness CSV 파서 — 테스트용 더미 CSV를 MeterEvent로 변환.
(프로덕션: 실제 witness 포맷은 별도 구현)
"""
import csv
import datetime as dt
from typing import TextIO, List
from apps.metering.schema import MeterEvent


def parse_witness_csv(f: TextIO) -> List[MeterEvent]:
    """
    CSV 형식: tenant,metric,corr_id,ts,value
    - ts는 ISO 8601 (YYYY-MM-DDTHH:MM:SS)
    - value는 float
    """
    reader = csv.DictReader(f)
    events = []
    for row in reader:
        tenant = row["tenant"].strip()
        metric = row["metric"].strip()
        corr_id = row["corr_id"].strip()
        ts_str = row["ts"].strip()
        value = float(row["value"].strip())

        # ISO → datetime (naive UTC assumed)
        ts = dt.datetime.fromisoformat(ts_str)

        ev = MeterEvent(
            tenant=tenant,
            metric=metric,
            corr_id=corr_id,
            ts=ts,
            value=value,
            tags={},
        )
        events.append(ev)
    return events
