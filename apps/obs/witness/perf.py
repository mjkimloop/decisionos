"""
apps/obs/witness/perf.py

성능 증빙 - reqlog CSV 파싱 및 p50/p95/p99, error_rate 요약
"""
from __future__ import annotations
import csv
import datetime as dt
from typing import TextIO, List, Dict, Any
from dataclasses import dataclass


@dataclass
class Req:
    """단일 요청 레코드"""

    ts: dt.datetime
    status: int
    latency_ms: float


def parse_reqlog_csv(f: TextIO) -> List[Req]:
    """
    reqlog CSV 파싱.

    형식: ts,status,latency_ms
    - ts: ISO 8601 형식 (YYYY-MM-DDTHH:MM:SS)
    - status: HTTP 상태 코드 (int)
    - latency_ms: 지연 시간 (float, 밀리초)

    Returns:
        요청 레코드 리스트
    """
    reader = csv.DictReader(f)
    reqs = []
    for row in reader:
        raw_ts = row["ts"].strip()
        normalized_ts = raw_ts.replace("Z", "+00:00") if raw_ts.endswith("Z") else raw_ts
        ts = dt.datetime.fromisoformat(normalized_ts)
        status = int(row["status"].strip())
        latency_ms = float(row["latency_ms"].strip())
        reqs.append(Req(ts=ts, status=status, latency_ms=latency_ms))
    return reqs


def _percentile(values: List[float], p: float) -> float:
    """
    Nearest-rank 퍼센타일 계산.

    Args:
        values: 정렬된 값 리스트
        p: 퍼센타일 (0.0 ~ 1.0)

    Returns:
        퍼센타일 값
    """
    if not values:
        return 0.0
    n = len(values)
    idx = max(0, min(n - 1, int(p * n)))
    return values[idx]


def summarize_perf(reqs: List[Req]) -> Dict[str, Any]:
    """
    요청 목록에서 성능 요약 산출.

    Returns:
        {
            "latency_ms": {"p50": float, "p95": float, "p99": float},
            "error_rate": float,
            "count": int,
            "window": {"start": str, "end": str}
        }

    경계 케이스:
        - 빈 입력 → {"count": 0}
    """
    if not reqs:
        return {"count": 0}

    # 지연 시간 정렬
    latencies = sorted([r.latency_ms for r in reqs])

    # 퍼센타일 계산
    p50 = _percentile(latencies, 0.50)
    p95 = _percentile(latencies, 0.95)
    p99 = _percentile(latencies, 0.99)

    # 에러율 계산 (status >= 500 or status == 429)
    error_count = sum(1 for r in reqs if r.status >= 500 or r.status == 429)
    error_rate = error_count / len(reqs) if reqs else 0.0

    # 시간 윈도우
    timestamps = [r.ts for r in reqs]
    window_start = min(timestamps).isoformat()
    window_end = max(timestamps).isoformat()

    return {
        "latency_ms": {"p50": round(p50, 2), "p95": round(p95, 2), "p99": round(p99, 2)},
        "error_rate": round(error_rate, 6),
        "count": len(reqs),
        "window": {"start": window_start, "end": window_end},
    }
