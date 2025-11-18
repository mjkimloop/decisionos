# Work Order v0.5.11t: Metrics System (Prometheus) - COMPLETE ✅

**Date**: 2025-11-16
**Scope**: Phase 3 - In-memory Prometheus-compatible metrics with RBAC tracking and readyz sliding windows

---

## Summary

Successfully implemented a lightweight in-memory Prometheus-compatible metrics system with:

1. **Metrics Registry** - Thread-safe Counter, Gauge, Info metrics with Prometheus text renderer
2. **RBAC Metrics** - Hot-reload checks/hits, allowed/forbidden counters, route matches, map ETag tracking
3. **readyz Metrics** - Sliding window success ratios (1m, 5m) using collections.deque
4. **/metrics Endpoints** - Prometheus text format (text/plain) for both Ops and Judge servers
5. **Comprehensive Tests** - 13/13 tests passing (6 RBAC + 7 readyz)

**Key Feature**: Zero external dependencies - all metrics in-memory, no Redis/Prometheus client required.

---

## Files Created

### Core Metrics Infrastructure

#### `apps/common/metrics.py` (129 lines)
Lightweight Prometheus-compatible metrics registry.

**Classes**:
- `Counter`: Monotonic increment-only counter
- `Gauge`: Arbitrary float value (can set/inc/dec)
- `Info`: Label-only metric (value always 1)
- `Registry`: Thread-safe registry with Prometheus text renderer
- `REG`: Global singleton instance

**Key Implementation**:
```python
class Registry:
    def render_text(self) -> str:
        """Render all metrics in Prometheus text exposition format."""
        lines = []
        for c in self._counters.values():
            lines.append(f"# TYPE {c.name} counter")
            lines.append(f"{c.name} {c.get()}")
        # ... gauges, info metrics
        return "\n".join(lines) + "\n"
```

**Thread Safety**: All metrics use `threading.Lock` for atomic operations.

---

### RBAC Metrics Integration

#### Modified: `apps/policy/rbac_enforce.py`
Added metrics collection points:

**Metrics Added**:
1. `rbac_reload_checks_total` - Counter incremented on every ensure_fresh() call
2. `rbac_reload_hit_total` - Counter incremented when map file SHA changes
3. `rbac_allowed_total` - Counter for successful RBAC checks
4. `rbac_forbidden_total` - Counter for failed RBAC checks (403)
5. `rbac_route_matches_total` - Counter for route pattern matches
6. `rbac_map_info{etag="..."}` - Info metric with current map SHA as label

**Collection Points**:
```python
def ensure_fresh(self):
    REG.counter("rbac_reload_checks_total").inc()
    # ... check file hash
    if current != self.sha:
        REG.counter("rbac_reload_hit_total").inc()
    REG.info("rbac_map_info", labels=("etag",)).set((self.sha,))

async def dispatch(self, request: Request, call_next):
    if matched:
        REG.counter("rbac_route_matches_total").inc()
    if access_denied:
        REG.counter("rbac_forbidden_total").inc()
    else:
        REG.counter("rbac_allowed_total").inc()
```

---

### readyz Sliding Window Metrics

#### Modified: `apps/judge/metrics_readyz.py` (68 lines)
Enhanced with sliding window tracking using `collections.deque`.

**New Features**:
- Two sliding windows: 1-minute (60s) and 5-minute (300s)
- Stores `(timestamp, ok)` tuples in deque
- Automatic trimming of old entries
- Success ratio calculation: `ok_count / total_count` (defaults to 1.0 if empty)

**Key Implementation**:
```python
class ReadyzMetrics:
    def __init__(self, window_1m: int = 60, window_5m: int = 300):
        self._window_1m: deque = deque()
        self._window_5m: deque = deque()

    def observe(self, ok: bool):
        now = time.time()
        self._window_1m.append((now, ok))
        self._window_5m.append((now, ok))
        self._trim_window(self._window_1m, now - self._window_1m_sec)
        self._trim_window(self._window_5m, now - self._window_5m_sec)

    def export_gauges(self):
        """Export sliding window success ratios to global metrics."""
        ratio_1m = ok_1m / total_1m if total_1m > 0 else 1.0
        ratio_5m = ok_5m / total_5m if total_5m > 0 else 1.0
        REG.gauge("readyz_success_ratio_1m").set(ratio_1m)
        REG.gauge("readyz_success_ratio_5m").set(ratio_5m)
```

**Metrics Exported**:
- `readyz_success_ratio_1m` - Success ratio over last 60 seconds
- `readyz_success_ratio_5m` - Success ratio over last 300 seconds

---

### /metrics Endpoints

#### Modified: `apps/ops/api.py`
Added Prometheus text endpoint:
```python
from apps.common.metrics import REG

@app.get("/metrics")
async def metrics():
    """Prometheus-compatible text metrics endpoint."""
    return PlainTextResponse(REG.render_text(), media_type="text/plain")
```

#### Modified: `apps/judge/server.py`
Added Prometheus text endpoint with readyz export:
```python
from apps.common.metrics import REG
from apps.judge.metrics_readyz import READYZ_METRICS

@app.get("/metrics")
async def metrics_endpoint(request: Request):
    # Export readyz sliding window gauges before rendering
    READYZ_METRICS.export_gauges()
    return PlainTextResponse(REG.render_text(), media_type="text/plain")
```

**Example Output** (text/plain):
```
# HELP rbac_reload_checks_total Total RBAC map reload checks
# TYPE rbac_reload_checks_total counter
rbac_reload_checks_total 42
# HELP rbac_allowed_total Total RBAC allowed requests
# TYPE rbac_allowed_total counter
rbac_allowed_total 128
# TYPE rbac_map_info gauge
rbac_map_info{etag="5bcdd633308d109fdad6fd5e6697406ea1182086da3c46b04633a63bbf2e2358"} 1
# TYPE readyz_success_ratio_1m gauge
readyz_success_ratio_1m 0.95
# TYPE readyz_success_ratio_5m gauge
readyz_success_ratio_5m 0.98
```

---

## Tests Created

### `tests/gates/gate_sec/test_rbac_metrics_hit_miss_v1.py` (85 lines)
**Tests**: 6/6 passed ✅

1. `test_rbac_reload_metrics_inc` - Reload check counter increments
2. `test_rbac_reload_hit_on_change` - Reload hit counter on file change
3. `test_rbac_map_etag_info_metric` - ETag info metric correctness
4. `test_rbac_allowed_forbidden_counters` - Allowed/forbidden counters
5. `test_rbac_route_matches_counter` - Route match counter
6. `test_metrics_render_text_prometheus_format` - Text format validation

**Key Test Pattern**:
```python
def test_rbac_reload_hit_on_change(tmp_path):
    state = RbacMapState(str(map_path), reload_sec=1, require_all=False)
    initial_hit = REG.counter("rbac_reload_hit_total").get()
    # Change map file
    time.sleep(1.1)
    write_map(map_path, ["new:scope"])
    state.ensure_fresh()
    assert REG.counter("rbac_reload_hit_total").get() > initial_hit
```

---

### `tests/gates/gate_aj/test_readyz_metrics_text_v1.py` (80 lines)
**Tests**: 7/7 passed ✅

1. `test_readyz_metrics_observe_increments_total` - Total counter increments
2. `test_readyz_metrics_observe_increments_fail` - Fail counter increments
3. `test_readyz_metrics_sliding_window_1m` - 1-minute window trimming
4. `test_readyz_metrics_export_gauges_ratio` - Success ratio calculation (3/4 = 0.75)
5. `test_readyz_metrics_export_gauges_empty_window` - Empty window defaults to 1.0
6. `test_metrics_text_endpoint_contains_readyz_gauges` - Text output validation
7. `test_readyz_metrics_last_status_updated` - Status tracking (ready/degraded)

**Key Test Pattern**:
```python
def test_readyz_metrics_sliding_window_1m():
    rm = ReadyzMetrics(window_1m=2, window_5m=5)
    rm.observe(True)
    rm.observe(False)
    time.sleep(2.1)
    rm.observe(True)
    # First two should be trimmed from 2-second window
    rm.export_gauges()
    ratio_1m = REG.gauge("readyz_success_ratio_1m").get()
    assert ratio_1m == 1.0  # Only last (True) remains
```

---

## Configuration

### pytest.ini
Added `gate_sec` marker:
```ini
markers =
    gate_sec: Gate-SEC (Security / RBAC / PII)
```

---

## Test Results

```bash
$ python -m pytest tests/gates/gate_sec/test_rbac_metrics_hit_miss_v1.py \
                   tests/gates/gate_aj/test_readyz_metrics_text_v1.py -v

======================== 13 passed, 1 warning in 7.28s =========================
```

**Breakdown**:
- RBAC metrics: 6/6 passed ✅
- readyz metrics: 7/7 passed ✅
- Total: **13/13 passed** ✅

---

## Acceptance Criteria - All Met ✅

- [x] Lightweight in-memory metrics registry (no external deps)
- [x] Prometheus text exposition format (/metrics endpoints)
- [x] RBAC reload checks/hits counters
- [x] RBAC allowed/forbidden/route_matches counters
- [x] RBAC map ETag as info metric with label
- [x] readyz sliding window (1m, 5m) with deque
- [x] readyz success ratio gauges (0.0 - 1.0)
- [x] Thread-safe implementations (all metrics use Lock)
- [x] /metrics endpoint on Ops API (text/plain)
- [x] /metrics endpoint on Judge server (text/plain)
- [x] Comprehensive test coverage (13 tests, all passing)

---

## Integration Points

**Ops API** ([apps/ops/api.py:150-153](apps/ops/api.py#L150-L153)):
```python
@app.get("/metrics")
async def metrics():
    return PlainTextResponse(REG.render_text(), media_type="text/plain")
```

**Judge Server** ([apps/judge/server.py:149-154](apps/judge/server.py#L149-L154)):
```python
@app.get("/metrics")
async def metrics_endpoint(request: Request):
    READYZ_METRICS.export_gauges()
    return PlainTextResponse(REG.render_text(), media_type="text/plain")
```

**RBAC Middleware** ([apps/policy/rbac_enforce.py:69-80](apps/policy/rbac_enforce.py#L69-L80)):
- Increments counters on reload checks, hits, allowed, forbidden
- Exports ETag as info metric

**readyz Health Checks** ([apps/judge/metrics_readyz.py:24-66](apps/judge/metrics_readyz.py#L24-L66)):
- Observes readyz checks in sliding windows
- Exports success ratios as gauges

---

## Prometheus Compatibility

**Text Format**: Fully compatible with Prometheus scraping
**Sample curl**:
```bash
curl http://localhost:8081/metrics
curl http://localhost:8082/metrics
```

**Grafana Query Examples**:
```promql
# RBAC reload hit rate
rate(rbac_reload_hit_total[5m])

# RBAC forbidden rate
rate(rbac_forbidden_total[1m])

# readyz success ratio (5m window)
readyz_success_ratio_5m
```

---

## Performance

- **In-memory only** - No disk/network I/O for metrics
- **Lock contention** - Minimal due to short critical sections
- **Window trimming** - O(k) where k = expired entries (amortized O(1))
- **Text rendering** - O(n) where n = total metrics (typically < 100)

---

## Next Steps

✅ Phase 1: Rate Limiter + PII Redaction (COMPLETE)
✅ Phase 2: RBAC Hot-Reload + readyz reason/metrics (COMPLETE)
✅ Phase 3: Prometheus Metrics (COMPLETE)

**Ready for**:
- Integration testing with real Prometheus scraper
- Production deployment with monitoring dashboards
- SLO alerting based on readyz_success_ratio metrics

---

**Status**: ✅ COMPLETE - All 13 tests passing, all acceptance criteria met
