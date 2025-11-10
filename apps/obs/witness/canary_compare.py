from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List


def load_csv(path: str | Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with Path(path).open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows.extend(reader)
    return rows


def summarize_perf(rows: List[Dict[str, str]]) -> Dict[str, float]:
    if not rows:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "error_rate": 0.0, "count": 0}
    latencies = sorted(float(r["latency_ms"]) for r in rows)
    count = len(latencies)
    err = sum(1 for r in rows if int(r["status"]) >= 500)
    p50 = _percentile(latencies, 0.5)
    p95 = _percentile(latencies, 0.95)
    p99 = _percentile(latencies, 0.99)
    return {
        "p50": round(p50, 2),
        "p95": round(p95, 2),
        "p99": round(p99, 2),
        "error_rate": round(err / count, 6),
        "count": count,
    }


def compare(control_csv: str | Path, canary_csv: str | Path) -> Dict[str, object]:
    control_rows = load_csv(control_csv)
    canary_rows = load_csv(canary_csv)
    control_perf = summarize_perf(control_rows)
    canary_perf = summarize_perf(canary_rows)
    deltas = _compute_deltas(control_perf, canary_perf, control_rows, canary_rows)
    return {"control_perf": control_perf, "canary_perf": canary_perf, "deltas": deltas}


def _compute_deltas(control_perf: Dict[str, float], canary_perf: Dict[str, float], control_rows, canary_rows):
    control_p95 = max(control_perf.get("p95", 1.0), 1.0)
    p95_rel = (canary_perf.get("p95", 0.0) - control_perf.get("p95", 0.0)) / control_p95
    error_delta = canary_perf.get("error_rate", 0.0) - control_perf.get("error_rate", 0.0)
    sig_control = _signature_rate(control_rows)
    sig_canary = _signature_rate(canary_rows)
    sig_delta = sig_canary - sig_control
    return {
        "p95_rel": round(p95_rel, 6),
        "error_delta": round(error_delta, 6),
        "sig_error_delta": round(sig_delta, 6),
    }


def _signature_rate(rows: List[Dict[str, str]]) -> float:
    if not rows:
        return 0.0
    return sum(1 for r in rows if r.get("signature_error") in ("1", "true", "True")) / len(rows)


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


__all__ = ["compare", "summarize_perf"]
