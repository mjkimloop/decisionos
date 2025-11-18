"""
gate_aj: readyz sliding window metrics and /metrics text endpoint
"""
import pytest
import time

from apps.common.metrics import REG
from apps.judge.metrics_readyz import ReadyzMetrics


@pytest.mark.gate_aj
def test_readyz_metrics_observe_increments_total():
    """ReadyzMetrics.observe() increments total counter."""
    rm = ReadyzMetrics()
    initial = rm.total
    rm.observe(True)
    assert rm.total == initial + 1


@pytest.mark.gate_aj
def test_readyz_metrics_observe_increments_fail():
    """ReadyzMetrics.observe(False) increments fail counter."""
    rm = ReadyzMetrics()
    initial_fail = rm.fail
    rm.observe(False)
    assert rm.fail == initial_fail + 1


@pytest.mark.gate_aj
def test_readyz_metrics_sliding_window_1m():
    """ReadyzMetrics maintains 1-minute sliding window."""
    rm = ReadyzMetrics(window_1m=2, window_5m=5)
    rm.observe(True)
    rm.observe(False)
    time.sleep(2.1)
    rm.observe(True)
    # First two should be trimmed
    snapshot = rm.snapshot()
    assert snapshot["total"] == 3
    # Check window has only recent entries
    rm.export_gauges()
    ratio_1m = REG.gauge("readyz_success_ratio_1m").get()
    # Only the last observation (True) remains in 1m window
    assert ratio_1m == 1.0


@pytest.mark.gate_aj
def test_readyz_metrics_export_gauges_ratio():
    """ReadyzMetrics.export_gauges() sets ratio gauges correctly."""
    rm = ReadyzMetrics(window_1m=60, window_5m=300)
    # 3 successes, 1 failure
    rm.observe(True)
    rm.observe(True)
    rm.observe(True)
    rm.observe(False)
    rm.export_gauges()
    ratio_1m = REG.gauge("readyz_success_ratio_1m").get()
    # 3 out of 4 = 0.75
    assert ratio_1m == 0.75


@pytest.mark.gate_aj
def test_readyz_metrics_export_gauges_empty_window():
    """ReadyzMetrics.export_gauges() returns 1.0 for empty window."""
    rm = ReadyzMetrics(window_1m=1, window_5m=5)
    time.sleep(1.1)
    rm.export_gauges()
    ratio_1m = REG.gauge("readyz_success_ratio_1m").get()
    # Empty window defaults to 1.0 (ready)
    assert ratio_1m == 1.0


@pytest.mark.gate_aj
def test_metrics_text_endpoint_contains_readyz_gauges():
    """Registry.render_text() includes readyz success ratio gauges."""
    rm = ReadyzMetrics()
    rm.observe(True)
    rm.observe(False)
    rm.export_gauges()
    text = REG.render_text()
    assert "readyz_success_ratio_1m" in text
    assert "readyz_success_ratio_5m" in text
    assert "# TYPE readyz_success_ratio_1m gauge" in text
    assert "# TYPE readyz_success_ratio_5m gauge" in text


@pytest.mark.gate_aj
def test_readyz_metrics_last_status_updated():
    """ReadyzMetrics.observe() updates last_status."""
    rm = ReadyzMetrics()
    rm.observe(True)
    snapshot = rm.snapshot()
    assert snapshot["last_status"] == "ready"
    rm.observe(False)
    snapshot = rm.snapshot()
    assert snapshot["last_status"] == "degraded"
