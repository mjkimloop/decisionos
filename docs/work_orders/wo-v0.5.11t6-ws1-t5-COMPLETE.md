# WS1-05: Label/Card/Cache Tenant Scope — COMPLETE

**Version:** v0.5.11t6-ws1-t5
**Date:** 2025-01-12
**Status:** ✅ **COMPLETE** (Full Implementation)

---

## Executive Summary

Implemented complete tenant-scoped card aggregation with label catalog overlays and ETag caching isolation.

**Key Deliverables:**
- ✅ Tenant-specific label catalog overlays
- ✅ Full `reason_trends` card implementation with tenant scoping
- ✅ Tenant-aware ETag store wrapper
- ✅ Comprehensive test suite (13 tests passing)

**Test Results:** 13 passed
**Code:** ~500 lines (implementation + tests)

---

## Implementation Details

### 1. Label Catalog Overlay System

**Purpose:** Allow tenants to customize label definitions and groups while inheriting from global catalog.

**Structure:**
```
configs/labels/
├── label_catalog_v2.json          # Global catalog (fallback)
└── overlay/
    ├── t1/
    │   └── label_catalog_v2.json  # Tenant t1 overlay
    └── t2/
        └── label_catalog_v2.json  # Tenant t2 overlay
```

**Load Priority:**
1. Try tenant overlay: `configs/labels/overlay/{tenant_id}/label_catalog_v2.json`
2. Fallback to global: `configs/labels/label_catalog_v2.json`
3. Return empty catalog if neither exists

**Example Overlay ([configs/labels/overlay/t1/label_catalog_v2.json](configs/labels/overlay/t1/label_catalog_v2.json)):**
```json
{
  "version": 2,
  "tenant_id": "t1",
  "groups": [
    {
      "name": "payments",
      "weight": 2.0,
      "description": "Payment processing group (high priority for t1)"
    },
    {
      "name": "auth",
      "weight": 1.5,
      "description": "Authentication group"
    }
  ],
  "labels": [
    {
      "name": "payment_declined",
      "type": "categorical",
      "group": "payments",
      "severity": "high"
    },
    {
      "name": "payment_success",
      "type": "categorical",
      "group": "payments",
      "severity": "low"
    },
    {
      "name": "auth_failed",
      "type": "categorical",
      "group": "auth",
      "severity": "medium"
    }
  ]
}
```

---

### 2. Reason Trends Card Implementation

**File:** [apps/ops/cards/reason_trends.py](apps/ops/cards/reason_trends.py) (202 lines)

**Key Functions:**

#### `load_label_catalog(tenant_id: str)`
```python
def load_label_catalog(tenant_id: str) -> Dict[str, Any]:
    """
    Load label catalog for tenant (global + overlay).

    Priority:
    1. Tenant overlay
    2. Global catalog (adds tenant_id)
    3. Empty catalog
    """
```

#### `compute_reason_trends(tenant_id, since, until, limit)`
```python
def compute_reason_trends(
    tenant_id: str,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Compute reason trends for tenant.

    - Validates tenant ID (fail-closed)
    - Loads tenant-specific catalog
    - Reads tenant-scoped evidence: var/evidence/{tenant}/reasons.jsonl
    - Aggregates by group/label with counts
    - Supports time range filtering
    - Respects limit

    Returns:
        {
          "tenant_id": str,
          "catalog_version": int,
          "time_range": {"since": str, "until": str},
          "groups": [{"name": str, "count": int}, ...],
          "labels": [{"name": str, "count": int}, ...],
          "total_events": int
        }
    """
```

**Evidence Path Convention:**
- `var/evidence/{tenant_id}/reasons.jsonl`
- Each line: `{"ts": "2025-01-12T10:00:00Z", "group": "payments", "label": "payment_declined"}`
- Missing group/label → `"unknown"`
- Invalid JSON lines → skipped

**Aggregation:**
- Groups sorted by count (descending)
- Labels sorted by count (descending)
- Top-N extraction via `top_n_labels()` and `top_n_groups()`

#### `top_n_labels(data, n=5)` / `top_n_groups(data, n=5)`
```python
def top_n_labels(data: Dict[str, Any], n: int = 5) -> List[Dict[str, Any]]:
    """Get top N labels from aggregated data (pre-sorted)"""
    return data.get("labels", [])[:n]
```

#### `filter_by_severity(data, tenant_id, severity)`
```python
def filter_by_severity(
    data: Dict[str, Any],
    tenant_id: str,
    severity: str
) -> List[Dict[str, Any]]:
    """
    Filter labels by severity level.

    Loads tenant catalog, builds severity map, filters labels.
    Severity levels: critical/high/medium/low
    """
```

---

### 3. Tenant-Scoped ETag Store

**File:** [apps/ops/etag_store.py](apps/ops/etag_store.py) (150 lines)

**Purpose:** Wrap core `ETagStore` with tenant-aware key namespacing for Cards API cache isolation.

**Key Function:**
```python
def ns_key(tenant_id: str, service: str, resource_key: str) -> str:
    """
    Generate tenant-namespaced ETag key.

    Format: {tenant}:{service}:{resource_key}

    Examples:
        ns_key("t1", "ops", "reason-trends") → "t1:ops:reason-trends"
        ns_key("acme-corp", "cards", "palette") → "acme-corp:cards:palette"
    """
```

**Class: `TenantETagStore`**
```python
class TenantETagStore:
    """Tenant-scoped ETag store wrapper"""

    def __init__(self, store: ETagStore, tenant_id: str, service: str = "ops"):
        self.store = store
        self.tenant_id = tenant_id
        self.service = service

    def put(self, resource_key: str, payload: Dict[str, Any]) -> str:
        """Store payload, return ETag"""
        namespaced = self._namespaced_key(resource_key)
        return self.store.put(namespaced, payload)

    def get(self, resource_key: str, etag: Optional[str] = None) -> Optional[Dict]:
        """Retrieve cached payload (with ETag validation)"""

    def cas(self, resource_key: str, old_etag, new_payload) -> tuple[bool, Optional[str]]:
        """Compare-and-swap with tenant namespacing"""

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate keys matching pattern within tenant scope"""
```

**Factory Function:**
```python
def get_tenant_etag_store(
    redis_client,
    tenant_id: str,
    service: str = "ops",
    ttl_ms: int = 600000
) -> TenantETagStore:
    """Create tenant-scoped ETag store with underlying base store"""
```

**Isolation Guarantee:**
- Redis keys: `dos:etag:{tenant}:{service}:{resource_key}`
- Cross-tenant cache collisions impossible
- 304 Not Modified responses tenant-specific

---

### 4. Tenant Configurations

**Created Tenants:** t1, t2

**File:** [configs/tenants/t1.yaml](configs/tenants/t1.yaml)
```yaml
tenant_id: t1
name: "Test Tenant 1"
status: active
created_at: "2025-01-12T00:00:00Z"
updated_at: "2025-01-12T00:00:00Z"

limits:
  max_qps: 1000
  max_storage_gb: 100
  max_users: 50

clock_skew_ms: 60000

slo_overlay:
  latency_p95_ms: 200.0
  latency_p99_ms: 500.0
  error_rate_percent: 1.0

label_overlay:
  base: "configs/labels/label_catalog_v2.json"
  tenant: "configs/labels/overlay/t1/label_catalog_v2.json"

billing:
  plan: "standard"
  billing_contact: "billing-t1@example.com"
  cost_center: "TEST-T1"
```

**File:** [configs/tenants/t2.yaml](configs/tenants/t2.yaml)
- Similar structure with higher QPS (2000), stricter SLOs

---

## Test Coverage

**File:** [tests/gates/gate_cards/test_cards_tenant_cache_and_topN_v1.py](tests/gates/gate_cards/test_cards_tenant_cache_and_topN_v1.py) (400 lines)

**Test Results:** ✅ 13/13 passed

| Test | Description |
|------|-------------|
| `test_load_tenant_label_catalog_overlay` | Load t1/t2 catalogs with correct groups/labels |
| `test_load_tenant_label_catalog_fallback_global` | Fallback to global catalog for nonexistent tenant |
| `test_compute_reason_trends_tenant_isolation` | Verify t1 and t2 have separate aggregations |
| `test_compute_reason_trends_time_range_filter` | Filter events by since/until timestamps |
| `test_compute_reason_trends_limit` | Limit parameter caps event processing |
| `test_top_n_labels` | Extract top N labels (sorted by count) |
| `test_top_n_groups` | Extract top N groups (sorted by count) |
| `test_filter_by_severity` | Filter labels by severity (high/medium/low) |
| `test_filter_by_severity_unknown_labels` | Unknown labels excluded from severity filter |
| `test_compute_reason_trends_invalid_json` | Skip malformed JSONL lines gracefully |
| `test_compute_reason_trends_empty_file` | Handle empty evidence file (0 events) |
| `test_compute_reason_trends_no_evidence_file` | Handle missing evidence file (0 events) |
| `test_compute_reason_trends_unknown_group_label` | Use "unknown" for missing group/label fields |

**Coverage:** Label loading, aggregation, filtering, edge cases, tenant isolation

---

## API Integration

### Example: Reason Trends Endpoint

```python
from apps.ops.cards.reason_trends import compute_reason_trends
from apps.common import require_tenant_context

@router.get("/cards/reason-trends")
def get_reason_trends(
    tenant_id: str = Depends(require_tenant),
    since: Optional[str] = Query(None),
    until: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get aggregated reason trends for tenant"""
    result = compute_reason_trends(
        tenant_id=tenant_id,
        since=since,
        until=until,
        limit=limit
    )

    # Optional: Cache with tenant-scoped ETag
    etag_store = get_tenant_etag_store(redis_client, tenant_id, service="cards")
    etag = etag_store.put("reason-trends", result)

    return JSONResponse(
        content=result,
        headers={"ETag": etag}
    )
```

**Request:**
```bash
curl "http://localhost:8081/ops/cards/reason-trends?tenant=t1&since=2025-01-01T00:00:00Z&limit=100"
```

**Response:**
```json
{
  "tenant_id": "t1",
  "catalog_version": 2,
  "time_range": {
    "since": "2025-01-01T00:00:00Z",
    "until": null
  },
  "groups": [
    {"name": "payments", "count": 42},
    {"name": "auth", "count": 18}
  ],
  "labels": [
    {"name": "payment_declined", "count": 30},
    {"name": "payment_success", "count": 12},
    {"name": "auth_failed", "count": 18}
  ],
  "total_events": 60
}
```

---

## File Summary

### Created Files (8)

**Configuration:**
- `configs/labels/overlay/t1/label_catalog_v2.json` (36 lines)
- `configs/labels/overlay/t2/label_catalog_v2.json` (36 lines)
- `configs/tenants/t1.yaml` (31 lines)
- `configs/tenants/t2.yaml` (31 lines)

**Implementation:**
- `apps/ops/cards/reason_trends.py` (202 lines)
- `apps/ops/etag_store.py` (150 lines)

**Tests:**
- `tests/gates/gate_cards/__init__.py` (3 lines)
- `tests/gates/gate_cards/test_cards_tenant_cache_and_topN_v1.py` (400 lines)

**Updated:**
- `pytest.ini` (added `gate_cards` marker)

**Total:** ~890 lines

---

## Performance Characteristics

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| `load_label_catalog()` | O(1) file read | Tenant overlay or global fallback |
| `compute_reason_trends()` | O(N) where N=events | Linear scan with limit cap |
| `top_n_labels()` | O(1) | Pre-sorted, just slicing |
| `filter_by_severity()` | O(M) where M=labels | Hash map lookup |
| ETag namespacing | O(1) | String prefix only |

**Bottleneck:** Evidence file I/O for large JSONL files
**Mitigation:** `limit` parameter caps processing

---

## Security & Isolation

**Guarantees:**
1. **Tenant validation:** `validate_tenant_id()` at entry (fail-closed)
2. **Evidence isolation:** Separate directories (`var/evidence/{tenant}/`)
3. **Label catalog isolation:** Overlay system prevents cross-tenant catalog bleed
4. **ETag cache isolation:** Namespace prefix `{tenant}:{service}:{key}`
5. **Aggregation isolation:** Only processes tenant-specific evidence

**Fail-Closed Behavior:**
- Invalid tenant → `ValueError` (caught by `require_tenant()` → HTTP 403)
- Missing evidence file → Empty result (0 events)
- Invalid JSON lines → Skipped, not errors

---

## Usage Examples

### Compute Trends for Tenant

```python
from apps.ops.cards.reason_trends import compute_reason_trends

result = compute_reason_trends(
    tenant_id="t1",
    since="2025-01-01T00:00:00Z",
    until="2025-01-12T23:59:59Z",
    limit=500
)

print(f"Total events: {result['total_events']}")
print(f"Top group: {result['groups'][0]}")
```

### Filter by Severity

```python
from apps.ops.cards.reason_trends import compute_reason_trends, filter_by_severity

data = compute_reason_trends("t1", limit=100)

critical_labels = filter_by_severity(data, "t1", "critical")
high_labels = filter_by_severity(data, "t1", "high")

print(f"Critical: {len(critical_labels)}, High: {len(high_labels)}")
```

### Top N Labels

```python
from apps.ops.cards.reason_trends import compute_reason_trends, top_n_labels

data = compute_reason_trends("t1", limit=100)

top_5 = top_n_labels(data, n=5)
for label in top_5:
    print(f"{label['name']}: {label['count']}")
```

### Tenant-Scoped ETag Caching

```python
from apps.ops.etag_store import get_tenant_etag_store
import redis

r = redis.Redis()
store = get_tenant_etag_store(r, tenant_id="t1", service="cards")

# Cache result
payload = {"data": [...]}
etag = store.put("reason-trends", payload)  # t1:cards:reason-trends

# Retrieve with validation
cached = store.get("reason-trends", etag)  # Returns payload

# Different tenant gets different cache
store_t2 = get_tenant_etag_store(r, tenant_id="t2", service="cards")
cached_t2 = store_t2.get("reason-trends", etag)  # Returns None (different namespace)
```

---

## Migration Notes

### New Dependencies

None (uses existing `pathlib`, `json`, `collections`)

### Breaking Changes

None (new functionality)

### Integration with Existing Code

**Cards API ([apps/ops/api_cards.py](apps/ops/api_cards.py)):**
- Already has `require_tenant()` dependency
- Can directly call `compute_reason_trends(tenant_id, ...)`
- Add ETag caching for performance

**Evidence Indexer ([apps/obs/evidence/indexer.py](apps/obs/evidence/indexer.py)):**
- Already writes to `var/evidence/{tenant}/` partitions
- `reason_trends` expects `reasons.jsonl` in same structure

---

## Operational Checklist

### Deployment

- [x] Create tenant configs (t1, t2)
- [x] Create label catalog overlays
- [x] Verify evidence directory structure
- [x] Run tests (13 passed)

### Monitoring

```bash
# Verify label catalogs
cat configs/labels/overlay/t1/label_catalog_v2.json
cat configs/labels/overlay/t2/label_catalog_v2.json

# Check evidence files
ls var/evidence/t1/reasons.jsonl
ls var/evidence/t2/reasons.jsonl

# Test aggregation
python -c "from apps.ops.cards.reason_trends import compute_reason_trends; print(compute_reason_trends('t1', limit=10))"
```

### Troubleshooting

**"Tenant not found":**
- Check `configs/tenants/t1.yaml` exists
- Verify `tenant_id` matches filename

**Empty aggregation:**
- Check `var/evidence/t1/reasons.jsonl` exists
- Verify JSONL format (one JSON object per line)

**Wrong labels:**
- Verify overlay catalog loaded: `load_label_catalog("t1")`
- Check label names match evidence events

---

## Next Steps (WS1-06)

**SLO Overlay Judge Integration:**
- Expand `apps/judge/slo_loader.py`
- Integrate tenant-specific SLO evaluation
- Add SLO violation reason codes

**Dependencies:**
- WS1-05 (this task) → WS1-06 (judge SLO overlay)

---

**Implementation Date:** 2025-01-12
**Status:** ✅ **COMPLETE**
**Test Results:** 13/13 passed
**Sign-off:** Claude Code v0.5.11t6-ws1-t5
