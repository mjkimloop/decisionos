"""
Gate Tenant — Tenant configuration and validation tests
"""
import pytest
import os
from pathlib import Path

pytestmark = pytest.mark.gate_tenant


def test_tenant_config_loads_default():
    """Test that default tenant config loads"""
    from apps.tenants import get_registry

    registry = get_registry()
    config = registry.get("default")

    assert config is not None
    assert config.tenant_id == "default"
    assert config.name == "Default Tenant"
    assert config.status == "active"


def test_tenant_config_loads_acme():
    """Test that acme-corp tenant config loads"""
    from apps.tenants import get_registry

    registry = get_registry()
    config = registry.get("acme-corp")

    assert config is not None
    assert config.tenant_id == "acme-corp"
    assert config.name == "ACME Corporation"
    assert config.status == "active"


def test_tenant_validate_active():
    """Test that validate_tenant_id accepts active tenants"""
    from apps.tenants import validate_tenant_id

    # Should not raise for active tenant
    validate_tenant_id("default")
    validate_tenant_id("acme-corp")


def test_tenant_validate_missing():
    """Test that validate_tenant_id rejects missing tenants (fail-closed)"""
    from apps.tenants import validate_tenant_id

    with pytest.raises(ValueError, match="not found"):
        validate_tenant_id("nonexistent-tenant")


def test_tenant_validate_invalid_id_format():
    """Test that tenant_id format validation works"""
    from apps.tenants import TenantConfig

    # Valid format
    config_valid = {
        "tenant_id": "valid-tenant-123",
        "name": "Valid",
        "status": "active",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }
    TenantConfig(config_valid)  # Should not raise

    # Invalid format (uppercase not allowed)
    config_invalid = {
        "tenant_id": "Invalid-TENANT",
        "name": "Invalid",
        "status": "active",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }
    with pytest.raises(ValueError, match="must contain only lowercase"):
        TenantConfig(config_invalid)


def test_tenant_config_limits():
    """Test tenant resource limits"""
    from apps.tenants import get_registry

    registry = get_registry()

    # Default tenant
    default_config = registry.get("default")
    assert default_config.get_max_qps() == 1000

    # ACME tenant (higher limits)
    acme_config = registry.get("acme-corp")
    assert acme_config.get_max_qps() == 5000


def test_tenant_clock_skew():
    """Test tenant-specific clock skew settings"""
    from apps.tenants import get_registry

    registry = get_registry()

    # Default tenant: 60 seconds
    default_config = registry.get("default")
    assert default_config.get_clock_skew_ms() == 60000

    # ACME tenant: 30 seconds (stricter)
    acme_config = registry.get("acme-corp")
    assert acme_config.get_clock_skew_ms() == 30000


def test_tenant_list_active():
    """Test listing active tenants"""
    from apps.tenants import get_registry

    registry = get_registry()
    active_tenants = registry.list_active()

    assert "default" in active_tenants
    assert "acme-corp" in active_tenants


def test_tenant_require_fail_closed():
    """Test that require() fails closed for invalid tenants"""
    from apps.tenants import get_registry

    registry = get_registry()

    # Should raise for nonexistent tenant
    with pytest.raises(ValueError, match="not found"):
        registry.require("invalid-tenant")


def test_tenant_config_validation_fail_closed():
    """Test that invalid tenant configs fail during load (fail-closed)"""
    from apps.tenants import TenantConfig

    # Missing required fields
    invalid_config = {
        "tenant_id": "test",
        # Missing name, status, etc.
    }

    with pytest.raises(KeyError):
        TenantConfig(invalid_config)


def test_tenant_status_validation():
    """Test that only active/suspended statuses are allowed"""
    from apps.tenants import TenantConfig

    valid_config = {
        "tenant_id": "test-tenant",
        "name": "Test",
        "status": "active",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }

    # Active status
    config_active = TenantConfig(valid_config)
    assert config_active.is_active()

    # Suspended status
    valid_config["status"] = "suspended"
    config_suspended = TenantConfig(valid_config)
    assert not config_suspended.is_active()

    # Invalid status
    valid_config["status"] = "unknown"
    with pytest.raises(ValueError, match="Invalid status"):
        TenantConfig(valid_config)
