"""
Reason Trends with Tenant Scoping

Computes aggregated reason trends with tenant isolation.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict


def load_label_catalog(tenant_id: str) -> Dict[str, Any]:
    """
    Load label catalog for tenant (global + overlay).

    Args:
        tenant_id: Tenant identifier

    Returns:
        Merged label catalog dict
    """
    # Try tenant overlay first
    overlay_path = Path(f"configs/labels/overlay/{tenant_id}/label_catalog_v2.json")

    if overlay_path.exists():
        with open(overlay_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Fallback to global catalog
    global_path = Path("configs/labels/label_catalog_v2.json")
    if global_path.exists():
        with open(global_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
            # Add tenant_id if not present
            if "tenant_id" not in catalog:
                catalog["tenant_id"] = tenant_id
            return catalog

    # Empty catalog (no overlay, no global)
    return {
        "version": "v2",
        "tenant_id": tenant_id,
        "groups": [],
        "labels": []
    }


def compute_reason_trends(
    tenant_id: str,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Compute reason trends for tenant.

    Args:
        tenant_id: Tenant identifier
        since: Start timestamp (ISO format)
        until: End timestamp (ISO format)
        limit: Maximum number of events to process

    Returns:
        Aggregated trends dict with tenant context
    """
    from apps.tenants import validate_tenant_id

    # Validate tenant
    validate_tenant_id(tenant_id)

    # Load tenant-specific catalog
    catalog = load_label_catalog(tenant_id)

    # Aggregate counts by group/label
    group_counts: Dict[str, int] = defaultdict(int)
    label_counts: Dict[str, int] = defaultdict(int)

    # Load tenant-scoped events
    events_path = Path(f"var/evidence/{tenant_id}/reasons.jsonl")
    events = []

    if events_path.exists():
        with open(events_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)

                    # Filter by time range if specified
                    if since and event.get("ts", "") < since:
                        continue
                    if until and event.get("ts", "") > until:
                        continue

                    events.append(event)

                    # Aggregate
                    group = event.get("group", "unknown")
                    label = event.get("label", "unknown")

                    group_counts[group] += 1
                    label_counts[label] += 1

                    if len(events) >= limit:
                        break

                except json.JSONDecodeError:
                    continue

    # Build response
    groups = [
        {"name": name, "count": count}
        for name, count in sorted(
            group_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
    ]

    labels = [
        {"name": name, "count": count}
        for name, count in sorted(
            label_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
    ]

    return {
        "tenant_id": tenant_id,
        "catalog_version": catalog.get("version", 2),
        "time_range": {
            "since": since,
            "until": until,
        },
        "groups": groups,
        "labels": labels,
        "total_events": len(events),
    }


def top_n_labels(
    data: Dict[str, Any],
    n: int = 5
) -> List[Dict[str, Any]]:
    """
    Get top N labels from aggregated data.

    Args:
        data: Aggregated trends data
        n: Number of top labels to return

    Returns:
        List of top N labels with counts
    """
    labels = data.get("labels", [])
    return labels[:n]


def top_n_groups(
    data: Dict[str, Any],
    n: int = 5
) -> List[Dict[str, Any]]:
    """
    Get top N groups from aggregated data.

    Args:
        data: Aggregated trends data
        n: Number of top groups to return

    Returns:
        List of top N groups with counts
    """
    groups = data.get("groups", [])
    return groups[:n]


def filter_by_severity(
    data: Dict[str, Any],
    tenant_id: str,
    severity: str
) -> List[Dict[str, Any]]:
    """
    Filter labels by severity level.

    Args:
        data: Aggregated trends data
        tenant_id: Tenant identifier
        severity: Severity level (critical/high/medium/low)

    Returns:
        List of labels matching severity
    """
    catalog = load_label_catalog(tenant_id)

    # Build severity map
    severity_map = {}
    for label_def in catalog.get("labels", []):
        label_name = label_def.get("name")
        label_severity = label_def.get("severity", "low")
        if label_name:
            severity_map[label_name] = label_severity

    # Filter
    filtered = []
    for label in data.get("labels", []):
        label_name = label.get("name")
        if severity_map.get(label_name) == severity:
            filtered.append(label)

    return filtered
