"""
gate_sec: RBAC metrics - reload checks/hits, allowed/forbidden, route matches, map ETag
"""
import pytest
import time
from pathlib import Path

from apps.common.metrics import REG
from apps.policy.rbac_enforce import RbacMapState


def write_map(path: Path, scopes: list[str]):
    path.write_text(f"routes:\n  - path: /ops/cards/*\n    method: GET\n    scopes: {scopes}\n", encoding="utf-8")


@pytest.mark.gate_sec
def test_rbac_reload_metrics_inc(tmp_path):
    """Reload check counter increments on ensure_fresh calls."""
    mapp = tmp_path / "rbac_map.yaml"
    write_map(mapp, ["ops:read"])
    state = RbacMapState(str(mapp), reload_sec=1, require_all=False)

    initial = REG.counter("rbac_reload_checks_total").get()
    # Wait for reload interval to trigger actual check
    time.sleep(1.1)
    state.ensure_fresh()
    assert REG.counter("rbac_reload_checks_total").get() > initial


@pytest.mark.gate_sec
def test_rbac_reload_hit_on_change(tmp_path):
    """Reload hit counter increments when map file changes."""
    mapp = tmp_path / "rbac_map.yaml"
    write_map(mapp, ["ops:read"])
    state = RbacMapState(str(mapp), reload_sec=1, require_all=False)

    initial_hit = REG.counter("rbac_reload_hit_total").get()
    # Change map
    time.sleep(1.1)
    write_map(mapp, ["ops:admin"])
    state.ensure_fresh()
    assert REG.counter("rbac_reload_hit_total").get() > initial_hit


@pytest.mark.gate_sec
def test_rbac_map_etag_info_metric(tmp_path):
    """RBAC map ETag is exported as info metric."""
    mapp = tmp_path / "rbac_map.yaml"
    write_map(mapp, ["ops:read"])
    state = RbacMapState(str(mapp), reload_sec=1, require_all=False)

    # Get SHA after initialization
    expected_sha = state.sha

    # Trigger ensure_fresh to export metric
    time.sleep(1.1)
    state.ensure_fresh()

    # Info metric exists
    info = REG.info("rbac_map_info", labels=("etag",))
    label_vals, val = info.get()
    assert val == 1
    assert len(label_vals) == 1
    assert label_vals[0] == expected_sha


@pytest.mark.gate_sec
def test_rbac_allowed_forbidden_counters():
    """RBAC allowed/forbidden counters exist and can increment."""
    initial_allowed = REG.counter("rbac_allowed_total").get()
    REG.counter("rbac_allowed_total").inc()
    assert REG.counter("rbac_allowed_total").get() == initial_allowed + 1

    initial_forbidden = REG.counter("rbac_forbidden_total").get()
    REG.counter("rbac_forbidden_total").inc()
    assert REG.counter("rbac_forbidden_total").get() == initial_forbidden + 1


@pytest.mark.gate_sec
def test_rbac_route_matches_counter():
    """RBAC route matches counter exists and can increment."""
    initial = REG.counter("rbac_route_matches_total").get()
    REG.counter("rbac_route_matches_total").inc()
    assert REG.counter("rbac_route_matches_total").get() == initial + 1


@pytest.mark.gate_sec
def test_metrics_render_text_prometheus_format():
    """Registry.render_text() produces Prometheus-compatible text."""
    # Ensure some metrics exist
    REG.counter("test_counter", "Test counter help").inc(5)
    REG.gauge("test_gauge", "Test gauge help").set(42.5)

    text = REG.render_text()
    assert "# HELP test_counter Test counter help" in text
    assert "# TYPE test_counter counter" in text
    assert "test_counter" in text
    assert "# HELP test_gauge Test gauge help" in text
    assert "# TYPE test_gauge gauge" in text
    assert "test_gauge 42.5" in text
