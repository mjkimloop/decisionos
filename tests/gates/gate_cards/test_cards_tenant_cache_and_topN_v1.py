"""
Gate Cards — Tenant-scoped cache and topN tests
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

pytestmark = pytest.mark.gate_cards


@pytest.fixture
def temp_evidence_dir():
    """Create temporary evidence directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_label_config(tmp_path):
    """Create temporary label catalog overlay"""
    overlay_base = tmp_path / "configs" / "labels" / "overlay"

    # Tenant t1 overlay
    t1_dir = overlay_base / "t1"
    t1_dir.mkdir(parents=True)
    t1_catalog = {
        "version": 2,
        "tenant_id": "t1",
        "groups": [
            {"name": "payments", "weight": 2.0}
        ],
        "labels": [
            {"name": "payment_declined", "type": "categorical", "group": "payments", "severity": "high"},
            {"name": "payment_success", "type": "categorical", "group": "payments", "severity": "low"}
        ]
    }
    with open(t1_dir / "label_catalog_v2.json", "w", encoding="utf-8") as f:
        json.dump(t1_catalog, f)

    # Tenant t2 overlay
    t2_dir = overlay_base / "t2"
    t2_dir.mkdir(parents=True)
    t2_catalog = {
        "version": 2,
        "tenant_id": "t2",
        "groups": [
            {"name": "api", "weight": 1.5}
        ],
        "labels": [
            {"name": "api_timeout", "type": "categorical", "group": "api", "severity": "critical"},
            {"name": "api_success", "type": "categorical", "group": "api", "severity": "low"}
        ]
    }
    with open(t2_dir / "label_catalog_v2.json", "w", encoding="utf-8") as f:
        json.dump(t2_catalog, f)

    return overlay_base


def test_load_tenant_label_catalog_overlay(temp_label_config, monkeypatch):
    """Test loading tenant-specific label catalog overlay"""
    from apps.ops.cards.reason_trends import load_label_catalog

    # Use actual tenant t1/t2 configs that exist in the project
    catalog_t1 = load_label_catalog("t1")

    assert catalog_t1["tenant_id"] == "t1"
    assert catalog_t1["version"] == 2
    assert len(catalog_t1["groups"]) == 2  # payments, auth
    assert catalog_t1["groups"][0]["name"] == "payments"
    assert len(catalog_t1["labels"]) == 3  # payment_declined, payment_success, auth_failed

    # Test t2 as well
    catalog_t2 = load_label_catalog("t2")

    assert catalog_t2["tenant_id"] == "t2"
    assert catalog_t2["version"] == 2
    assert len(catalog_t2["groups"]) == 2  # api, database


def test_load_tenant_label_catalog_fallback_global():
    """Test fallback to global catalog when overlay not found"""
    from apps.ops.cards.reason_trends import load_label_catalog

    # Non-existent tenant should fallback to global catalog or return empty
    catalog = load_label_catalog("nonexistent-tenant")

    assert catalog["version"] in ["v2", 2]  # Support both formats
    assert "tenant_id" in catalog
    assert "groups" in catalog
    assert "labels" in catalog


def test_compute_reason_trends_tenant_isolation(temp_evidence_dir):
    """Test that reason trends are computed per tenant"""
    from apps.ops.cards.reason_trends import compute_reason_trends

    # Create tenant directories with evidence
    t1_dir = Path(temp_evidence_dir) / "t1"
    t1_dir.mkdir(parents=True)

    t2_dir = Path(temp_evidence_dir) / "t2"
    t2_dir.mkdir(parents=True)

    # Write events for tenant t1
    t1_events = t1_dir / "reasons.jsonl"
    with open(t1_events, "w", encoding="utf-8") as f:
        f.write(json.dumps({"ts": "2025-01-12T10:00:00Z", "group": "payments", "label": "payment_declined"}) + "\n")
        f.write(json.dumps({"ts": "2025-01-12T10:01:00Z", "group": "payments", "label": "payment_declined"}) + "\n")
        f.write(json.dumps({"ts": "2025-01-12T10:02:00Z", "group": "payments", "label": "payment_success"}) + "\n")

    # Write events for tenant t2
    t2_events = t2_dir / "reasons.jsonl"
    with open(t2_events, "w", encoding="utf-8") as f:
        f.write(json.dumps({"ts": "2025-01-12T10:00:00Z", "group": "api", "label": "api_timeout"}) + "\n")
        f.write(json.dumps({"ts": "2025-01-12T10:01:00Z", "group": "api", "label": "api_success"}) + "\n")

    # Mock the evidence path
    import apps.ops.cards.reason_trends as reason_trends_module
    original_path = reason_trends_module.Path

    def mock_path(p):
        if "var/evidence" in str(p):
            return Path(str(p).replace("var/evidence", temp_evidence_dir))
        return original_path(p)

    reason_trends_module.Path = mock_path

    try:
        # Compute trends for t1
        result_t1 = compute_reason_trends("t1", limit=100)

        assert result_t1["tenant_id"] == "t1"
        assert result_t1["total_events"] == 3
        assert len(result_t1["groups"]) == 1
        assert result_t1["groups"][0]["name"] == "payments"
        assert result_t1["groups"][0]["count"] == 3

        # Check labels
        assert len(result_t1["labels"]) == 2
        declined = next(l for l in result_t1["labels"] if l["name"] == "payment_declined")
        assert declined["count"] == 2

        # Compute trends for t2
        result_t2 = compute_reason_trends("t2", limit=100)

        assert result_t2["tenant_id"] == "t2"
        assert result_t2["total_events"] == 2
        assert len(result_t2["groups"]) == 1
        assert result_t2["groups"][0]["name"] == "api"

    finally:
        reason_trends_module.Path = original_path


def test_compute_reason_trends_time_range_filter(temp_evidence_dir):
    """Test time range filtering in reason trends"""
    from apps.ops.cards.reason_trends import compute_reason_trends

    t1_dir = Path(temp_evidence_dir) / "t1"
    t1_dir.mkdir(parents=True)

    t1_events = t1_dir / "reasons.jsonl"
    with open(t1_events, "w", encoding="utf-8") as f:
        f.write(json.dumps({"ts": "2025-01-10T10:00:00Z", "group": "g1", "label": "l1"}) + "\n")
        f.write(json.dumps({"ts": "2025-01-12T10:00:00Z", "group": "g1", "label": "l1"}) + "\n")
        f.write(json.dumps({"ts": "2025-01-15T10:00:00Z", "group": "g1", "label": "l1"}) + "\n")

    import apps.ops.cards.reason_trends as reason_trends_module
    original_path = reason_trends_module.Path
    reason_trends_module.Path = lambda p: Path(str(p).replace("var/evidence", temp_evidence_dir)) if "var/evidence" in str(p) else original_path(p)

    try:
        # Filter by since
        result = compute_reason_trends("t1", since="2025-01-12T00:00:00Z", limit=100)
        assert result["total_events"] == 2

        # Filter by until
        result = compute_reason_trends("t1", until="2025-01-12T23:59:59Z", limit=100)
        assert result["total_events"] == 2

        # Filter by both
        result = compute_reason_trends("t1", since="2025-01-11T00:00:00Z", until="2025-01-14T00:00:00Z", limit=100)
        assert result["total_events"] == 1

    finally:
        reason_trends_module.Path = original_path


def test_compute_reason_trends_limit(temp_evidence_dir):
    """Test limit parameter in reason trends"""
    from apps.ops.cards.reason_trends import compute_reason_trends

    t1_dir = Path(temp_evidence_dir) / "t1"
    t1_dir.mkdir(parents=True)

    t1_events = t1_dir / "reasons.jsonl"
    with open(t1_events, "w", encoding="utf-8") as f:
        for i in range(50):
            f.write(json.dumps({"ts": f"2025-01-12T10:{i:02d}:00Z", "group": "g1", "label": "l1"}) + "\n")

    import apps.ops.cards.reason_trends as reason_trends_module
    original_path = reason_trends_module.Path
    reason_trends_module.Path = lambda p: Path(str(p).replace("var/evidence", temp_evidence_dir)) if "var/evidence" in str(p) else original_path(p)

    try:
        result = compute_reason_trends("t1", limit=10)
        assert result["total_events"] == 10

    finally:
        reason_trends_module.Path = original_path


def test_top_n_labels():
    """Test top N labels extraction"""
    from apps.ops.cards.reason_trends import top_n_labels

    data = {
        "labels": [
            {"name": "l1", "count": 100},
            {"name": "l2", "count": 50},
            {"name": "l3", "count": 25},
            {"name": "l4", "count": 10},
            {"name": "l5", "count": 5},
            {"name": "l6", "count": 1},
        ]
    }

    top3 = top_n_labels(data, n=3)

    assert len(top3) == 3
    assert top3[0]["name"] == "l1"
    assert top3[1]["name"] == "l2"
    assert top3[2]["name"] == "l3"


def test_top_n_groups():
    """Test top N groups extraction"""
    from apps.ops.cards.reason_trends import top_n_groups

    data = {
        "groups": [
            {"name": "g1", "count": 200},
            {"name": "g2", "count": 150},
            {"name": "g3", "count": 100},
        ]
    }

    top2 = top_n_groups(data, n=2)

    assert len(top2) == 2
    assert top2[0]["name"] == "g1"
    assert top2[1]["name"] == "g2"


def test_filter_by_severity(temp_label_config, monkeypatch):
    """Test filtering labels by severity"""
    from apps.ops.cards.reason_trends import filter_by_severity

    # Use actual tenant t1 with its real label catalog
    data = {
        "labels": [
            {"name": "payment_declined", "count": 100},
            {"name": "payment_success", "count": 50},
            {"name": "unknown_label", "count": 10},
        ]
    }

    high_severity = filter_by_severity(data, "t1", "high")

    assert len(high_severity) == 1
    assert high_severity[0]["name"] == "payment_declined"

    low_severity = filter_by_severity(data, "t1", "low")

    assert len(low_severity) == 1
    assert low_severity[0]["name"] == "payment_success"


def test_filter_by_severity_unknown_labels():
    """Test filtering with labels not in catalog"""
    from apps.ops.cards.reason_trends import filter_by_severity

    data = {
        "labels": [
            {"name": "unknown1", "count": 100},
            {"name": "unknown2", "count": 50},
        ]
    }

    # Unknown labels should not match any severity
    result = filter_by_severity(data, "t1", "high")
    assert len(result) == 0


def test_compute_reason_trends_invalid_json(temp_evidence_dir):
    """Test handling of invalid JSON in evidence file"""
    from apps.ops.cards.reason_trends import compute_reason_trends

    t1_dir = Path(temp_evidence_dir) / "t1"
    t1_dir.mkdir(parents=True)

    t1_events = t1_dir / "reasons.jsonl"
    with open(t1_events, "w", encoding="utf-8") as f:
        f.write(json.dumps({"ts": "2025-01-12T10:00:00Z", "group": "g1", "label": "l1"}) + "\n")
        f.write("INVALID JSON LINE\n")
        f.write(json.dumps({"ts": "2025-01-12T10:01:00Z", "group": "g1", "label": "l2"}) + "\n")

    import apps.ops.cards.reason_trends as reason_trends_module
    original_path = reason_trends_module.Path
    reason_trends_module.Path = lambda p: Path(str(p).replace("var/evidence", temp_evidence_dir)) if "var/evidence" in str(p) else original_path(p)

    try:
        result = compute_reason_trends("t1", limit=100)

        # Should skip invalid line and process valid ones
        assert result["total_events"] == 2

    finally:
        reason_trends_module.Path = original_path


def test_compute_reason_trends_empty_file(temp_evidence_dir):
    """Test handling of empty evidence file"""
    from apps.ops.cards.reason_trends import compute_reason_trends

    t1_dir = Path(temp_evidence_dir) / "t1"
    t1_dir.mkdir(parents=True)

    t1_events = t1_dir / "reasons.jsonl"
    t1_events.touch()

    import apps.ops.cards.reason_trends as reason_trends_module
    original_path = reason_trends_module.Path
    reason_trends_module.Path = lambda p: Path(str(p).replace("var/evidence", temp_evidence_dir)) if "var/evidence" in str(p) else original_path(p)

    try:
        result = compute_reason_trends("t1", limit=100)

        assert result["total_events"] == 0
        assert result["groups"] == []
        assert result["labels"] == []

    finally:
        reason_trends_module.Path = original_path


def test_compute_reason_trends_no_evidence_file(temp_evidence_dir):
    """Test handling when evidence file does not exist"""
    from apps.ops.cards.reason_trends import compute_reason_trends

    import apps.ops.cards.reason_trends as reason_trends_module
    original_path = reason_trends_module.Path
    reason_trends_module.Path = lambda p: Path(str(p).replace("var/evidence", temp_evidence_dir)) if "var/evidence" in str(p) else original_path(p)

    try:
        result = compute_reason_trends("t1", limit=100)

        # Should return empty result when file doesn't exist
        assert result["total_events"] == 0
        assert result["groups"] == []
        assert result["labels"] == []

    finally:
        reason_trends_module.Path = original_path


def test_compute_reason_trends_unknown_group_label():
    """Test handling of events with missing group/label fields"""
    from apps.ops.cards.reason_trends import compute_reason_trends
    import tempfile

    temp_dir = tempfile.mkdtemp()
    try:
        t1_dir = Path(temp_dir) / "t1"
        t1_dir.mkdir(parents=True)

        t1_events = t1_dir / "reasons.jsonl"
        with open(t1_events, "w", encoding="utf-8") as f:
            f.write(json.dumps({"ts": "2025-01-12T10:00:00Z"}) + "\n")  # No group/label
            f.write(json.dumps({"ts": "2025-01-12T10:01:00Z", "group": "g1"}) + "\n")  # No label
            f.write(json.dumps({"ts": "2025-01-12T10:02:00Z", "label": "l1"}) + "\n")  # No group

        import apps.ops.cards.reason_trends as reason_trends_module
        original_path = reason_trends_module.Path
        reason_trends_module.Path = lambda p: Path(str(p).replace("var/evidence", temp_dir)) if "var/evidence" in str(p) else original_path(p)

        try:
            result = compute_reason_trends("t1", limit=100)

            # Should use "unknown" for missing fields
            assert result["total_events"] == 3
            assert any(g["name"] == "unknown" for g in result["groups"])
            assert any(l["name"] == "unknown" for l in result["labels"])

        finally:
            reason_trends_module.Path = original_path
    finally:
        shutil.rmtree(temp_dir)
