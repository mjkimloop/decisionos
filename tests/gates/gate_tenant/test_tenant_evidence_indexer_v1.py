"""
Gate Tenant — Evidence indexer tenant filtering tests
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path

pytestmark = pytest.mark.gate_tenant


@pytest.fixture
def temp_evidence_dir():
    """Create temporary evidence directory with test data"""
    temp_dir = tempfile.mkdtemp()
    evidence_path = Path(temp_dir)

    # Create evidence files for different tenants
    evidence_files = [
        {
            "filename": "ev_tenant_a_1.json",
            "meta": {"tenant": "tenant-a", "generated_at": "2025-01-15T10:00:00Z"},
            "witness": {"user_id": "user-a-1"},
            "usage": {},
            "rating": {},
            "quota": {},
            "budget": {},
            "anomaly": {},
            "integrity": {"signature_sha256": "dummy"},
        },
        {
            "filename": "ev_tenant_a_2.json",
            "meta": {"tenant": "tenant-a", "generated_at": "2025-01-15T11:00:00Z"},
            "witness": {"user_id": "user-a-2"},
            "usage": {},
            "rating": {},
            "quota": {},
            "budget": {},
            "anomaly": {},
            "integrity": {"signature_sha256": "dummy"},
        },
        {
            "filename": "ev_tenant_b_1.json",
            "meta": {"tenant": "tenant-b", "generated_at": "2025-01-15T10:00:00Z"},
            "witness": {"user_id": "user-b-1"},
            "usage": {},
            "rating": {},
            "quota": {},
            "budget": {},
            "anomaly": {},
            "integrity": {"signature_sha256": "dummy"},
        },
        {
            "filename": "ev_no_tenant.json",
            "meta": {"generated_at": "2025-01-15T10:00:00Z"},  # No tenant field
            "witness": {"user_id": "user-unknown"},
            "usage": {},
            "rating": {},
            "quota": {},
            "budget": {},
            "anomaly": {},
            "integrity": {"signature_sha256": "dummy"},
        },
    ]

    for ev_file in evidence_files:
        filename = ev_file.pop("filename")
        filepath = evidence_path / filename
        filepath.write_text(json.dumps(ev_file, indent=2), encoding="utf-8")

    yield str(evidence_path)

    # Cleanup
    shutil.rmtree(temp_dir)


def test_evidence_indexer_no_filter(temp_evidence_dir):
    """Test indexer without tenant filter returns all evidence"""
    from apps.obs.evidence.indexer import scan_dir

    index = scan_dir(temp_evidence_dir)

    assert index["summary"]["count"] == 4
    assert len(index["files"]) == 4


def test_evidence_indexer_tenant_filter_a(temp_evidence_dir):
    """Test indexer with tenant filter returns only tenant-a evidence"""
    from apps.obs.evidence.indexer import scan_dir

    index = scan_dir(temp_evidence_dir, tenant_filter="tenant-a")

    assert index["summary"]["count"] == 2
    assert len(index["files"]) == 2
    assert index["tenant_filter"] == "tenant-a"

    # All files should be for tenant-a
    for file_info in index["files"]:
        assert file_info["tenant"] == "tenant-a"


def test_evidence_indexer_tenant_filter_b(temp_evidence_dir):
    """Test indexer with tenant filter returns only tenant-b evidence"""
    from apps.obs.evidence.indexer import scan_dir

    index = scan_dir(temp_evidence_dir, tenant_filter="tenant-b")

    assert index["summary"]["count"] == 1
    assert len(index["files"]) == 1
    assert index["tenant_filter"] == "tenant-b"

    # File should be for tenant-b
    assert index["files"][0]["tenant"] == "tenant-b"


def test_evidence_indexer_tenant_filter_nonexistent(temp_evidence_dir):
    """Test indexer with filter for nonexistent tenant returns empty"""
    from apps.obs.evidence.indexer import scan_dir

    index = scan_dir(temp_evidence_dir, tenant_filter="nonexistent-tenant")

    assert index["summary"]["count"] == 0
    assert len(index["files"]) == 0
    assert index["tenant_filter"] == "nonexistent-tenant"


def test_evidence_indexer_tenant_aggregation(temp_evidence_dir):
    """Test indexer includes tenant-level aggregations"""
    from apps.obs.evidence.indexer import scan_dir

    index = scan_dir(temp_evidence_dir)

    # Check by_tenant aggregations
    assert "by_tenant" in index["summary"]
    by_tenant = index["summary"]["by_tenant"]

    assert "tenant-a" in by_tenant
    assert "tenant-b" in by_tenant
    assert "unknown" in by_tenant  # For evidence without tenant field

    assert by_tenant["tenant-a"]["count"] == 2
    assert by_tenant["tenant-b"]["count"] == 1
    assert by_tenant["unknown"]["count"] == 1


def test_evidence_indexer_tenant_aggregation_with_filter(temp_evidence_dir):
    """Test tenant aggregations work correctly with filters"""
    from apps.obs.evidence.indexer import scan_dir

    index = scan_dir(temp_evidence_dir, tenant_filter="tenant-a")

    by_tenant = index["summary"]["by_tenant"]

    # Only tenant-a should be in aggregations
    assert "tenant-a" in by_tenant
    assert "tenant-b" not in by_tenant
    assert by_tenant["tenant-a"]["count"] == 2


def test_evidence_indexer_tenant_field_extraction(temp_evidence_dir):
    """Test that tenant field is correctly extracted from meta"""
    from apps.obs.evidence.indexer import scan_dir

    index = scan_dir(temp_evidence_dir)

    # Find specific files
    files_by_name = {f["path"]: f for f in index["files"]}

    assert files_by_name["ev_tenant_a_1.json"]["tenant"] == "tenant-a"
    assert files_by_name["ev_tenant_b_1.json"]["tenant"] == "tenant-b"
    assert files_by_name["ev_no_tenant.json"]["tenant"] is None


def test_evidence_write_index_with_tenant_filter(temp_evidence_dir):
    """Test write_index with tenant filter"""
    from apps.obs.evidence.indexer import write_index

    output_path = Path(temp_evidence_dir) / "index_tenant_a.json"

    # Write index with tenant filter
    write_index(
        root=temp_evidence_dir,
        out=str(output_path),
        tenant_filter="tenant-a"
    )

    # Read back and verify
    with open(output_path, "r", encoding="utf-8") as f:
        index = json.load(f)

    assert index["tenant_filter"] == "tenant-a"
    assert index["summary"]["count"] == 2


def test_tenant_isolation_mixed_input_fail_closed(temp_evidence_dir):
    """Test that mixing tenant filters produces correct isolated results"""
    from apps.obs.evidence.indexer import scan_dir

    # Scan with filter A
    index_a = scan_dir(temp_evidence_dir, tenant_filter="tenant-a")

    # Scan with filter B
    index_b = scan_dir(temp_evidence_dir, tenant_filter="tenant-b")

    # Results should be completely isolated
    assert index_a["summary"]["count"] == 2
    assert index_b["summary"]["count"] == 1

    # No overlap in file lists
    files_a = {f["path"] for f in index_a["files"]}
    files_b = {f["path"] for f in index_b["files"]}
    assert files_a.isdisjoint(files_b)

    # Tenant aggregations should only show their own tenant
    assert "tenant-b" not in index_a["summary"]["by_tenant"]
    assert "tenant-a" not in index_b["summary"]["by_tenant"]
