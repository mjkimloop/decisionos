#!/usr/bin/env python3
"""PII circuit breaker monitoring job.

Periodically checks PII middleware performance and triggers circuit breaker
if error rates or latency exceed thresholds.

Usage:
    python -m jobs.pii_circuit_breaker_monitor
    python -m jobs.pii_circuit_breaker_monitor --interval 60

Environment:
    PII_METRICS_PATH                Path to metrics file (default: var/metrics/pii_latest.json)
    PII_BREAKER_ERROR_THRESHOLD     Error rate threshold (default: 0.05)
    PII_BREAKER_P99_THRESHOLD_MS    P99 latency threshold (default: 100)
    PII_BREAKER_MIN_SAMPLES         Min samples (default: 100)
    PII_BREAKER_INTERVAL_SEC        Check interval (default: 30)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from apps.security.pii_circuit_breaker import (
    CircuitBreakerMetrics,
    PIICircuitBreaker,
)


def load_metrics(metrics_path: Path) -> CircuitBreakerMetrics | None:
    """Load PII metrics from file."""
    if not metrics_path.exists():
        return None

    try:
        with open(metrics_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return CircuitBreakerMetrics(
            total_requests=data.get("total_requests", 0),
            failed_requests=data.get("failed_requests", 0),
            p99_latency_ms=data.get("p99_latency_ms", 0),
            timestamp=data.get("timestamp", time.time()),
        )
    except Exception as e:
        print(f"[pii-monitor ERROR] Failed to load metrics: {e}", file=sys.stderr)
        return None


def main() -> int:
    """Main entry point."""
    import os

    parser = argparse.ArgumentParser(description="PII circuit breaker monitor")
    parser.add_argument(
        "--interval", type=int, default=30, help="Check interval (seconds)"
    )
    parser.add_argument(
        "--once", action="store_true", help="Run once and exit"
    )
    args = parser.parse_args()

    # Load configuration from environment
    metrics_path = Path(
        os.environ.get("PII_METRICS_PATH", "var/metrics/pii_latest.json")
    )
    error_threshold = float(
        os.environ.get("PII_BREAKER_ERROR_THRESHOLD", "0.05")
    )
    p99_threshold_ms = float(
        os.environ.get("PII_BREAKER_P99_THRESHOLD_MS", "100")
    )
    min_samples = int(os.environ.get("PII_BREAKER_MIN_SAMPLES", "100"))
    interval_sec = int(
        os.environ.get("PII_BREAKER_INTERVAL_SEC", str(args.interval))
    )

    print("=" * 60)
    print("  PII CIRCUIT BREAKER MONITOR")
    print(f"  Metrics path: {metrics_path}")
    print(f"  Error threshold: {error_threshold:.2%}")
    print(f"  P99 threshold: {p99_threshold_ms}ms")
    print(f"  Min samples: {min_samples}")
    print(f"  Interval: {interval_sec}s")
    print("=" * 60)

    # Initialize circuit breaker
    breaker = PIICircuitBreaker(
        error_rate_threshold=error_threshold,
        p99_latency_threshold_ms=p99_threshold_ms,
        min_samples=min_samples,
    )

    # Print initial state
    state = breaker.get_state()
    print(f"\nInitial state: {state.state}")
    print(f"  Reason: {state.reason}")
    print(f"  Timestamp: {state.timestamp}")

    # Monitor loop
    iteration = 0
    while True:
        iteration += 1
        print(f"\n[Iteration {iteration}] Checking metrics...")

        # Load metrics
        metrics = load_metrics(metrics_path)

        if metrics is None:
            print("  No metrics available (skipping check)")
        else:
            print(f"  Total requests: {metrics.total_requests}")
            print(f"  Failed requests: {metrics.failed_requests}")
            print(f"  P99 latency: {metrics.p99_latency_ms:.1f}ms")

            # Check circuit breaker
            new_state = breaker.check(metrics)
            print(f"  Circuit breaker state: {new_state}")

            # Print state change
            if new_state != state.state:
                print(f"  ⚠ State changed: {state.state} → {new_state}")
                state = breaker.get_state()

        # Exit if --once
        if args.once:
            break

        # Sleep until next check
        time.sleep(interval_sec)

    return 0


if __name__ == "__main__":
    sys.exit(main())
