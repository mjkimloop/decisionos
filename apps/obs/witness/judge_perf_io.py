from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List


@dataclass
class JudgeRequest:
    ts: str
    status: int
    latency_ms: float
    signature_error: bool


def parse_judge_log_csv(path: str | Path) -> List[JudgeRequest]:
    path = Path(path)
    rows: List[JudgeRequest] = []
    with path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(
                JudgeRequest(
                    ts=_normalize_ts(row.get("ts", "")),
                    status=int(row.get("status", "0")),
                    latency_ms=float(row.get("latency_ms", "0")),
                    signature_error=row.get("signature_error", row.get("verify_error", "0")) in ("1", "true", "True"),
                )
            )
    return rows


def summarize_judge_perf(requests: Iterable[JudgeRequest]) -> dict:
    reqs = list(requests)
    total = len(reqs)
    if total == 0:
        return {
            "latency_ms": {"p50": 0.0, "p95": 0.0, "p99": 0.0},
            "availability": 0.0,
            "error_rate": 0.0,
            "signature_error_rate": 0.0,
            "count": 0,
            "window": {},
        }

    latencies = sorted(r.latency_ms for r in reqs)
    latency = {
        "p50": round(_percentile(latencies, 0.5), 2),
        "p95": round(_percentile(latencies, 0.95), 2),
        "p99": round(_percentile(latencies, 0.99), 2),
    }
    five_xx = sum(1 for r in reqs if r.status >= 500)
    errorish = sum(1 for r in reqs if r.status >= 500 or r.status == 429)
    sigerr = sum(1 for r in reqs if r.signature_error)

    availability = 1.0 - (five_xx / total)
    error_rate = errorish / total
    sig_rate = sigerr / total

    return {
        "latency_ms": latency,
        "availability": round(availability, 6),
        "error_rate": round(error_rate, 6),
        "signature_error_rate": round(sig_rate, 6),
        "count": total,
        "window": {
            "start": reqs[0].ts,
            "end": reqs[-1].ts,
        },
    }


def _percentile(values: List[float], fraction: float) -> float:
    if not values:
        return 0.0
    k = (len(values) - 1) * fraction
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return float(values[int(k)])
    d0 = values[f] * (c - k)
    d1 = values[c] * (k - f)
    return float(d0 + d1)


__all__ = ["JudgeRequest", "parse_judge_log_csv", "summarize_judge_perf"]


def _normalize_ts(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    normalized = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
    try:
        ts = datetime.fromisoformat(normalized)
    except ValueError:  # pragma: no cover - defensive
        return raw
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    else:
        ts = ts.astimezone(timezone.utc)
    return ts.isoformat().replace("+00:00", "Z")
