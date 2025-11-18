"""Tests for Prometheus metrics text export."""
from __future__ import annotations

import pytest


@pytest.mark.metrics
def test_metrics_registry_counter():
    """Test: Counter increments correctly."""
    from apps.metrics.registry import MetricRegistry

    registry = MetricRegistry()

    # Increment without labels
    import asyncio
    asyncio.run(registry.inc("test_counter"))
    asyncio.run(registry.inc("test_counter", n=5))

    # Increment with labels
    asyncio.run(registry.inc("test_labeled", {"status": "success"}))
    asyncio.run(registry.inc("test_labeled", {"status": "error"}))

    text = registry.export_prom_text()

    assert "test_counter 6" in text
    assert "test_labeled{status=\"success\"} 1" in text
    assert "test_labeled{status=\"error\"} 1" in text


@pytest.mark.metrics
def test_metrics_prom_text_format():
    """Test: Prometheus text format is valid."""
    from apps.metrics.registry import METRICS

    text = METRICS.export_prom_text()

    # Should have newline at end
    assert text.endswith("\n")

    # Should contain default counters
    assert "decisionos_rbac_eval_total" in text or text.startswith("decisionos_")


@pytest.mark.metrics
def test_metrics_concurrent_increments():
    """Test: Concurrent increments are thread-safe."""
    from apps.metrics.registry import MetricRegistry
    import asyncio

    registry = MetricRegistry()

    async def increment_many():
        tasks = []
        for i in range(100):
            tasks.append(registry.inc("concurrent_test"))
        await asyncio.gather(*tasks)

    asyncio.run(increment_many())

    text = registry.export_prom_text()
    assert "concurrent_test 100" in text
