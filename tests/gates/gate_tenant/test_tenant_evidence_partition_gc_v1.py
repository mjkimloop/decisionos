"""
Gate Tenant — Evidence partition and GC tests
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta

pytestmark = pytest.mark.gate_tenant


@pytest.fixture
def temp_partition_base():
    """Create temporary partitioned evidence directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


def test_partition_manager_get_partition_path():
    """Test partition path generation"""
    from apps.obs.evidence.partition import EvidencePartition

    pm = EvidencePartition("var/evidence")
    date = datetime(2025, 1, 15, tzinfo=timezone.utc)

    path = pm.get_partition_path("tenant-a", date)

    # Check path components (OS-independent)
    assert path.parts[-3:] == ("var", "evidence", "tenant-a") or \
           path.parts[-2:] == ("tenant-a", "2025-01")
    assert path.name == "2025-01"


def test_partition_manager_ensure_partition(temp_partition_base):
    """Test partition directory creation"""
    from apps.obs.evidence.partition import EvidencePartition

    pm = EvidencePartition(temp_partition_base)
    date = datetime(2025, 1, 15, tzinfo=timezone.utc)

    path = pm.ensure_partition("tenant-a", date)

    assert path.exists()
    assert path.is_dir()
    assert path.name == "2025-01"


def test_partition_manager_list_partitions(temp_partition_base):
    """Test listing partitions for tenant"""
    from apps.obs.evidence.partition import EvidencePartition

    pm = EvidencePartition(temp_partition_base)

    # Create partitions for different months
    pm.ensure_partition("tenant-a", datetime(2025, 1, 1, tzinfo=timezone.utc))
    pm.ensure_partition("tenant-a", datetime(2025, 2, 1, tzinfo=timezone.utc))
    pm.ensure_partition("tenant-a", datetime(2025, 3, 1, tzinfo=timezone.utc))

    partitions = pm.list_partitions("tenant-a")

    assert len(partitions) == 3
    assert partitions[0].name == "2025-01"
    assert partitions[1].name == "2025-02"
    assert partitions[2].name == "2025-03"


def test_partition_manager_tenant_isolation(temp_partition_base):
    """Test that tenants have isolated partitions"""
    from apps.obs.evidence.partition import EvidencePartition

    pm = EvidencePartition(temp_partition_base)

    # Create partitions for two tenants, same month
    pm.ensure_partition("tenant-a", datetime(2025, 1, 1, tzinfo=timezone.utc))
    pm.ensure_partition("tenant-b", datetime(2025, 1, 1, tzinfo=timezone.utc))

    partitions_a = pm.list_partitions("tenant-a")
    partitions_b = pm.list_partitions("tenant-b")

    assert len(partitions_a) == 1
    assert len(partitions_b) == 1
    assert "tenant-a" in str(partitions_a[0])
    assert "tenant-b" in str(partitions_b[0])


def test_partition_manager_list_all_tenants(temp_partition_base):
    """Test listing partitions for all tenants"""
    from apps.obs.evidence.partition import EvidencePartition

    pm = EvidencePartition(temp_partition_base)

    # Create partitions for multiple tenants
    pm.ensure_partition("tenant-a", datetime(2025, 1, 1, tzinfo=timezone.utc))
    pm.ensure_partition("tenant-a", datetime(2025, 2, 1, tzinfo=timezone.utc))
    pm.ensure_partition("tenant-b", datetime(2025, 1, 1, tzinfo=timezone.utc))

    all_partitions = pm.list_all_tenant_partitions()

    assert "tenant-a" in all_partitions
    assert "tenant-b" in all_partitions
    assert len(all_partitions["tenant-a"]) == 2
    assert len(all_partitions["tenant-b"]) == 1


def test_partition_manager_get_evidence_path():
    """Test evidence file path generation"""
    from apps.obs.evidence.partition import EvidencePartition

    pm = EvidencePartition("var/evidence")
    date = datetime(2025, 1, 15, tzinfo=timezone.utc)

    # WIP evidence
    path_wip = pm.get_evidence_path("tenant-a", "ev123", date, locked=False)
    assert path_wip.name == "evidence_ev123.json"
    assert "tenant-a" in path_wip.parts
    assert "2025-01" in path_wip.parts

    # LOCKED evidence
    path_locked = pm.get_evidence_path("tenant-a", "ev123", date, locked=True)
    assert path_locked.name == "evidence_ev123.locked.json"
    assert "tenant-a" in path_locked.parts
    assert "2025-01" in path_locked.parts


def test_partition_manager_valid_partition_name():
    """Test partition name validation"""
    from apps.obs.evidence.partition import EvidencePartition

    pm = EvidencePartition()

    # Valid names
    assert pm._is_valid_partition_name("2025-01")
    assert pm._is_valid_partition_name("2025-12")
    assert pm._is_valid_partition_name("2000-06")

    # Invalid names
    assert not pm._is_valid_partition_name("2025-13")  # Invalid month
    assert not pm._is_valid_partition_name("2025-00")  # Invalid month
    assert not pm._is_valid_partition_name("202501")   # Missing dash
    assert not pm._is_valid_partition_name("2025-1")   # Wrong format
    assert not pm._is_valid_partition_name("random")   # Not a date


def test_gc_config_tenant_retention():
    """Test loading tenant-specific retention policies"""
    import yaml
    from pathlib import Path

    config_path = Path("configs/evidence/retention.yaml")

    if not config_path.exists():
        pytest.skip("Retention config not found")

    with open(config_path, "r", encoding="utf-8") as f:
        policy = yaml.safe_load(f)

    # Check default policy
    assert "default" in policy
    assert "wip_days" in policy["default"]
    assert "locked_days" in policy["default"]

    # Check tenant policies
    assert "tenants" in policy
    assert "default" in policy["tenants"]
    assert "acme-corp" in policy["tenants"]

    # ACME should have stricter WIP retention
    acme_policy = policy["tenants"]["acme-corp"]
    default_policy = policy["tenants"]["default"]

    assert acme_policy["wip_days"] <= default_policy["wip_days"]
    assert acme_policy["locked_days"] >= default_policy["locked_days"]


def test_partition_manager_empty_tenant():
    """Test behavior with non-existent tenant"""
    from apps.obs.evidence.partition import EvidencePartition

    pm = EvidencePartition("var/evidence")

    partitions = pm.list_partitions("nonexistent-tenant")

    assert partitions == []


def test_get_partition_manager():
    """Test partition manager factory function"""
    from apps.obs.evidence.partition import get_partition_manager

    pm = get_partition_manager("custom/path")

    assert pm.base_path == Path("custom/path")
