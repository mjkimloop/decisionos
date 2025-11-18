"""Tests for PII middleware circuit breaker."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from apps.security.pii_circuit_breaker import (
    CircuitBreakerMetrics,
    PIICircuitBreaker,
)


@pytest.fixture
def temp_state_file(tmp_path):
    """Temporary state file for testing."""
    return str(tmp_path / "pii_breaker.json")


@pytest.mark.gate_ops
def test_breaker_initial_state(temp_state_file):
    """Test: Circuit breaker starts in enabled state."""
    breaker = PIICircuitBreaker(state_file=temp_state_file)
    state = breaker.get_state()

    assert state.state == "enabled"
    assert state.reason == "initial state"


@pytest.mark.gate_ops
def test_breaker_opens_on_high_error_rate(temp_state_file):
    """Test: Circuit breaker opens on high error rate."""
    breaker = PIICircuitBreaker(
        state_file=temp_state_file,
        error_rate_threshold=0.05,  # 5%
        min_samples=100,
    )

    # Simulate high error rate (10%)
    metrics = CircuitBreakerMetrics(
        total_requests=1000,
        failed_requests=100,  # 10% error rate
        p99_latency_ms=50,
        timestamp=time.time(),
    )

    new_state = breaker.check(metrics)

    assert new_state == "disabled_auto"
    assert "error_rate" in breaker.get_state().reason


@pytest.mark.gate_ops
def test_breaker_opens_on_high_latency(temp_state_file):
    """Test: Circuit breaker opens on high latency."""
    breaker = PIICircuitBreaker(
        state_file=temp_state_file,
        p99_latency_threshold_ms=100,  # 100ms
        min_samples=100,
    )

    # Simulate high latency (200ms)
    metrics = CircuitBreakerMetrics(
        total_requests=1000,
        failed_requests=10,  # 1% error rate (OK)
        p99_latency_ms=200,  # 200ms (TOO HIGH)
        timestamp=time.time(),
    )

    new_state = breaker.check(metrics)

    assert new_state == "disabled_auto"
    assert "p99" in breaker.get_state().reason


@pytest.mark.gate_ops
def test_breaker_stays_enabled_on_healthy_metrics(temp_state_file):
    """Test: Circuit breaker stays enabled with healthy metrics."""
    breaker = PIICircuitBreaker(
        state_file=temp_state_file,
        error_rate_threshold=0.05,
        p99_latency_threshold_ms=100,
        min_samples=100,
    )

    # Simulate healthy metrics
    metrics = CircuitBreakerMetrics(
        total_requests=1000,
        failed_requests=10,  # 1% error rate (OK)
        p99_latency_ms=50,  # 50ms (OK)
        timestamp=time.time(),
    )

    new_state = breaker.check(metrics)

    assert new_state == "enabled"


@pytest.mark.gate_ops
def test_breaker_auto_recovery(temp_state_file):
    """Test: Circuit breaker auto-recovers when metrics improve."""
    breaker = PIICircuitBreaker(
        state_file=temp_state_file,
        error_rate_threshold=0.05,
        min_samples=100,
    )

    # First: trigger circuit breaker
    bad_metrics = CircuitBreakerMetrics(
        total_requests=1000,
        failed_requests=100,  # 10% error rate
        p99_latency_ms=50,
        timestamp=time.time(),
    )

    breaker.check(bad_metrics)
    assert breaker.get_state().state == "disabled_auto"

    # Second: metrics improve
    good_metrics = CircuitBreakerMetrics(
        total_requests=1000,
        failed_requests=10,  # 1% error rate
        p99_latency_ms=50,
        timestamp=time.time(),
    )

    new_state = breaker.check(good_metrics)

    assert new_state == "enabled"
    assert "recovered" in breaker.get_state().reason


@pytest.mark.gate_ops
def test_breaker_manual_disable(temp_state_file):
    """Test: Manual disable overrides automatic state."""
    breaker = PIICircuitBreaker(state_file=temp_state_file)

    breaker.disable_manual("ops override")

    assert breaker.get_state().state == "disabled_manual"
    assert breaker.get_state().reason == "ops override"


@pytest.mark.gate_ops
def test_breaker_manual_disable_persists(temp_state_file):
    """Test: Manual disable persists across good metrics."""
    breaker = PIICircuitBreaker(state_file=temp_state_file)

    breaker.disable_manual("ops override")

    # Try to check with healthy metrics
    good_metrics = CircuitBreakerMetrics(
        total_requests=1000,
        failed_requests=10,
        p99_latency_ms=50,
        timestamp=time.time(),
    )

    new_state = breaker.check(good_metrics)

    # Should stay manually disabled
    assert new_state == "disabled_manual"


@pytest.mark.gate_ops
def test_breaker_manual_enable(temp_state_file):
    """Test: Manual enable re-enables circuit breaker."""
    breaker = PIICircuitBreaker(state_file=temp_state_file)

    # Disable manually
    breaker.disable_manual("ops override")
    assert breaker.get_state().state == "disabled_manual"

    # Re-enable manually
    breaker.enable_manual("ops re-enable")

    assert breaker.get_state().state == "enabled"
    assert breaker.get_state().reason == "ops re-enable"


@pytest.mark.gate_ops
def test_breaker_min_samples_threshold(temp_state_file):
    """Test: Circuit breaker ignores metrics below min_samples."""
    breaker = PIICircuitBreaker(
        state_file=temp_state_file,
        error_rate_threshold=0.05,
        min_samples=100,
    )

    # Simulate high error rate but low sample count
    metrics = CircuitBreakerMetrics(
        total_requests=50,  # Below min_samples
        failed_requests=25,  # 50% error rate (but not enough samples)
        p99_latency_ms=50,
        timestamp=time.time(),
    )

    new_state = breaker.check(metrics)

    # Should stay enabled (not enough samples)
    assert new_state == "enabled"


@pytest.mark.gate_ops
def test_breaker_state_persistence(temp_state_file):
    """Test: Circuit breaker state persists across restarts."""
    # First instance: open circuit
    breaker1 = PIICircuitBreaker(
        state_file=temp_state_file,
        error_rate_threshold=0.05,
        min_samples=100,
    )

    bad_metrics = CircuitBreakerMetrics(
        total_requests=1000,
        failed_requests=100,
        p99_latency_ms=50,
        timestamp=time.time(),
    )

    breaker1.check(bad_metrics)
    assert breaker1.get_state().state == "disabled_auto"

    # Second instance: should load disabled state
    breaker2 = PIICircuitBreaker(state_file=temp_state_file)

    assert breaker2.get_state().state == "disabled_auto"


@pytest.mark.gate_ops
def test_breaker_combined_thresholds(temp_state_file):
    """Test: Circuit breaker triggers on combined threshold violations."""
    breaker = PIICircuitBreaker(
        state_file=temp_state_file,
        error_rate_threshold=0.05,
        p99_latency_threshold_ms=100,
        min_samples=100,
    )

    # Simulate both high error rate and high latency
    metrics = CircuitBreakerMetrics(
        total_requests=1000,
        failed_requests=100,  # 10% error rate
        p99_latency_ms=200,  # 200ms latency
        timestamp=time.time(),
    )

    new_state = breaker.check(metrics)

    assert new_state == "disabled_auto"
    # Should mention both violations
    reason = breaker.get_state().reason
    assert "error_rate" in reason
    assert "p99" in reason
