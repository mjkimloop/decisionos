from __future__ import annotations

from typing import List, Dict

from .schema import Witness


def compute_p95(latencies_ms: List[float]) -> float:
    if not latencies_ms:
        return 0.0
    s = sorted(latencies_ms)
    k = int(max(0, round(0.95 * (len(s) - 1))))
    return float(s[k])


def export_witness(
    period_start: str,
    period_end: str,
    events: List[Dict],
    *,
    build_id: str,
    commit_sha: str,
    source_id: str = "exporter_x",
) -> Witness:
    # events: [{"latency_ms":..,"err":0/1,"cost_krw":..,"cite_ok":0/1,"parity_delta":..}, ...]
    n = len(events)
    if n == 0:
        cov = 0.0
        dropped = 0
        lat_p95 = 0.0
        lat_p99 = 0.0
        err = 0.0
        cost = 0.0
        cite = None
        parity = None
    else:
        cov = 1.0
        dropped = 0
        lats = [e.get("latency_ms", 0.0) for e in events]
        lat_p95 = compute_p95(lats)
        lat_p99 = compute_p95(sorted(lats)[: int(len(lats) * 0.99)] or lats)
        err = sum(1 for e in events if e.get("err", 0)) / n
        costs = [e.get("cost_krw", 0.0) for e in events]
        cost = sum(costs)
        cites = [e.get("cite_ok") for e in events if "cite_ok" in e]
        cite = (
            (sum(1 for c in cites if c) / len(cites))
            if cites
            else None
        )
        parities = [e.get("parity_delta") for e in events if "parity_delta" in e]
        parity = (sum(parities) / len(parities)) if parities else None

    witness = Witness(
        period_start=period_start,
        period_end=period_end,
        sample_n=n,
        coverage_ratio=cov,
        dropped_spans=dropped,
        latency_p95=lat_p95,
        latency_p99=lat_p99,
        err_rate=err,
        cost_krw=cost,
        citation_cov=cite,
        parity_delta=parity,
        build_id=build_id,
        commit_sha=commit_sha,
        source_id=source_id,
    )
    return witness.seal()


__all__ = ["compute_p95", "export_witness"]
