"""PII middleware circuit breaker for automatic fail-safe shutdown.

Monitors PII redaction performance and automatically disables the middleware
if error rates exceed thresholds to prevent production incidents.

Features:
  - Automatic shutdown on high error rate (>5% failures)
  - Automatic shutdown on high latency (p99 > 100ms)
  - Manual override capability
  - State persistence across restarts
  - Slack alerts on state changes
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Circuit breaker states
State = Literal["enabled", "disabled_auto", "disabled_manual"]

# Default thresholds
DEFAULT_ERROR_RATE_THRESHOLD = 0.05  # 5%
DEFAULT_P99_LATENCY_THRESHOLD_MS = 100  # 100ms
DEFAULT_MIN_SAMPLES = 100  # Minimum samples before opening circuit


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker decision."""

    total_requests: int
    failed_requests: int
    p99_latency_ms: float
    timestamp: float


@dataclass
class CircuitBreakerState:
    """Circuit breaker state."""

    state: State
    reason: str
    timestamp: float
    last_metrics: CircuitBreakerMetrics | None = None


class PIICircuitBreaker:
    """Circuit breaker for PII middleware."""

    def __init__(
        self,
        state_file: str = "var/runtime/pii_circuit_breaker.json",
        error_rate_threshold: float = DEFAULT_ERROR_RATE_THRESHOLD,
        p99_latency_threshold_ms: float = DEFAULT_P99_LATENCY_THRESHOLD_MS,
        min_samples: int = DEFAULT_MIN_SAMPLES,
    ):
        self.state_file = Path(state_file)
        self.error_rate_threshold = error_rate_threshold
        self.p99_latency_threshold_ms = p99_latency_threshold_ms
        self.min_samples = min_samples

        # Load or initialize state
        self._state = self._load_state()

    def _load_state(self) -> CircuitBreakerState:
        """Load state from disk or initialize."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                return CircuitBreakerState(
                    state=data["state"],
                    reason=data["reason"],
                    timestamp=data["timestamp"],
                    last_metrics=None,  # Don't persist metrics
                )
            except Exception as e:
                print(f"[pii-breaker WARN] Failed to load state: {e}")

        # Default: enabled
        return CircuitBreakerState(
            state="enabled",
            reason="initial state",
            timestamp=time.time(),
        )

    def _save_state(self) -> None:
        """Save state to disk."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "state": self._state.state,
                "reason": self._state.reason,
                "timestamp": self._state.timestamp,
            }

            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[pii-breaker ERROR] Failed to save state: {e}")

    def check(self, metrics: CircuitBreakerMetrics) -> State:
        """Check metrics and update circuit breaker state.

        Args:
            metrics: Current metrics

        Returns:
            Current state after check
        """
        # If manually disabled, keep disabled
        if self._state.state == "disabled_manual":
            return self._state.state

        # Check if we have enough samples
        if metrics.total_requests < self.min_samples:
            # Not enough data, keep current state
            return self._state.state

        # Calculate error rate
        error_rate = (
            metrics.failed_requests / metrics.total_requests
            if metrics.total_requests > 0
            else 0
        )

        # Check thresholds
        should_disable = False
        reason = ""

        if error_rate > self.error_rate_threshold:
            should_disable = True
            reason = f"error_rate={error_rate:.2%} > {self.error_rate_threshold:.2%}"

        if metrics.p99_latency_ms > self.p99_latency_threshold_ms:
            should_disable = True
            if reason:
                reason += f", p99={metrics.p99_latency_ms:.1f}ms > {self.p99_latency_threshold_ms}ms"
            else:
                reason = (
                    f"p99={metrics.p99_latency_ms:.1f}ms > {self.p99_latency_threshold_ms}ms"
                )

        # Update state if needed
        if should_disable and self._state.state == "enabled":
            self._state = CircuitBreakerState(
                state="disabled_auto",
                reason=reason,
                timestamp=time.time(),
                last_metrics=metrics,
            )
            self._save_state()
            self._send_alert("disabled", reason, metrics)
            print(f"[pii-breaker] Circuit opened: {reason}")

        elif not should_disable and self._state.state == "disabled_auto":
            # Auto-recovery (metrics back to normal)
            self._state = CircuitBreakerState(
                state="enabled",
                reason="metrics recovered",
                timestamp=time.time(),
                last_metrics=metrics,
            )
            self._save_state()
            self._send_alert("enabled", "metrics recovered", metrics)
            print(f"[pii-breaker] Circuit closed: metrics recovered")

        return self._state.state

    def get_state(self) -> CircuitBreakerState:
        """Get current state."""
        return self._state

    def disable_manual(self, reason: str = "manual override") -> None:
        """Manually disable PII middleware."""
        self._state = CircuitBreakerState(
            state="disabled_manual",
            reason=reason,
            timestamp=time.time(),
        )
        self._save_state()
        self._send_alert("disabled_manual", reason, None)
        print(f"[pii-breaker] Manually disabled: {reason}")

    def enable_manual(self, reason: str = "manual override") -> None:
        """Manually enable PII middleware."""
        self._state = CircuitBreakerState(
            state="enabled",
            reason=reason,
            timestamp=time.time(),
        )
        self._save_state()
        self._send_alert("enabled_manual", reason, None)
        print(f"[pii-breaker] Manually enabled: {reason}")

    def _send_alert(
        self,
        event: str,
        reason: str,
        metrics: CircuitBreakerMetrics | None,
    ) -> None:
        """Send Slack alert on state change."""
        webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
        if not webhook_url:
            return

        emoji = "🚨" if event.startswith("disabled") else "✅"
        color = "danger" if event.startswith("disabled") else "good"

        fields = [
            {"title": "Event", "value": event, "short": True},
            {"title": "Reason", "value": reason, "short": True},
        ]

        if metrics:
            error_rate = (
                metrics.failed_requests / metrics.total_requests
                if metrics.total_requests > 0
                else 0
            )
            fields.extend([
                {"title": "Error Rate", "value": f"{error_rate:.2%}", "short": True},
                {"title": "P99 Latency", "value": f"{metrics.p99_latency_ms:.1f}ms", "short": True},
                {"title": "Total Requests", "value": str(metrics.total_requests), "short": True},
            ])

        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"{emoji} PII Middleware Circuit Breaker",
                    "text": f"State changed: {event}",
                    "fields": fields,
                    "footer": "DecisionOS PII Circuit Breaker",
                    "ts": int(time.time()),
                }
            ]
        }

        try:
            import urllib.request

            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status != 200:
                    print(f"[pii-breaker WARN] Slack alert failed: HTTP {response.status}")
        except Exception as e:
            print(f"[pii-breaker ERROR] Failed to send Slack alert: {e}")


def should_enable_pii_middleware() -> bool:
    """Check if PII middleware should be enabled (for use in middleware init).

    Returns:
        True if enabled, False if disabled
    """
    breaker = PIICircuitBreaker()
    state = breaker.get_state()
    return state.state == "enabled"
