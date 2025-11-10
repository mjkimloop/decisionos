"""
Claude's independent implementation of witness exporter.
Uses different algorithms from exporter_x for diversity.
"""
from .schema import Witness
import statistics

def percentile(data: list[float], p: float) -> float:
    """Calculate percentile using linear interpolation method"""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    if len(sorted_data) == 1:
        return float(sorted_data[0])
    k = (len(sorted_data) - 1) * p
    f = int(k)
    c = k - f
    if f + 1 < len(sorted_data):
        return float(sorted_data[f] + c * (sorted_data[f + 1] - sorted_data[f]))
    return float(sorted_data[f])

def export_witness(period_start: str, period_end: str, events: list[dict], *,
                   build_id: str, commit_sha: str, source_id: str="exporter_c") -> Witness:
    """
    Independent implementation using different statistical methods.
    Events format: [{"latency_ms":..,"err":0/1,"cost_krw":..,"cite_ok":0/1,"parity_delta":..}, ...]
    """
    n = len(events)

    if n == 0:
        return Witness(
            period_start=period_start, period_end=period_end,
            sample_n=0, coverage_ratio=0.0, dropped_spans=0,
            latency_p95=0.0, latency_p99=0.0, err_rate=0.0, cost_krw=0.0,
            citation_cov=None, parity_delta=None,
            build_id=build_id, commit_sha=commit_sha, source_id=source_id
        ).seal()

    # Extract latencies
    latencies = [e.get("latency_ms", 0.0) for e in events]

    # Calculate percentiles using interpolation
    lat_p95 = percentile(latencies, 0.95)
    lat_p99 = percentile(latencies, 0.99)

    # Error rate
    error_count = sum(1 for e in events if e.get("err", 0) != 0)
    err_rate = error_count / n

    # Total cost
    total_cost = sum(e.get("cost_krw", 0.0) for e in events)

    # Citation coverage (if present)
    citation_events = [e for e in events if "cite_ok" in e]
    if citation_events:
        citation_ok_count = sum(1 for e in citation_events if e.get("cite_ok"))
        cite_cov = citation_ok_count / len(citation_events)
    else:
        cite_cov = None

    # Parity delta (if present)
    parity_events = [e.get("parity_delta") for e in events if "parity_delta" in e]
    if parity_events:
        parity = statistics.mean(parity_events)
    else:
        parity = None

    witness = Witness(
        period_start=period_start, period_end=period_end,
        sample_n=n, coverage_ratio=1.0, dropped_spans=0,
        latency_p95=lat_p95, latency_p99=lat_p99,
        err_rate=err_rate, cost_krw=total_cost,
        citation_cov=cite_cov, parity_delta=parity,
        build_id=build_id, commit_sha=commit_sha, source_id=source_id
    )

    return witness.seal()
