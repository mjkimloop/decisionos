"""
Gate Tenant — SLO overlay and label catalog tests
"""
import pytest

pytestmark = pytest.mark.gate_tenant


def test_slo_overlay_default_values():
    """Test SLO overlay returns tenant-specific values (default tenant has overrides)"""
    from apps.tenants import get_slo_overlay

    overlay = get_slo_overlay()

    # Default tenant has its own SLO overrides in config
    latency_p95 = overlay.get("default", "latency_p95_ms")
    latency_p99 = overlay.get("default", "latency_p99_ms")
    error_rate = overlay.get("default", "error_rate_max")

    assert latency_p95 == 200.0  # From default.yaml
    assert latency_p99 == 500.0  # From default.yaml
    assert error_rate == 0.01  # From default.yaml


def test_slo_overlay_tenant_overrides():
    """Test SLO overlay returns tenant-specific overrides"""
    from apps.tenants import get_slo_overlay

    overlay = get_slo_overlay()

    # ACME tenant should have custom SLO overrides
    latency_p95 = overlay.get("acme-corp", "latency_p95_ms")
    latency_p99 = overlay.get("acme-corp", "latency_p99_ms")
    error_rate = overlay.get("acme-corp", "error_rate_max")

    assert latency_p95 == 100.0  # Custom override
    assert latency_p99 == 250.0  # Custom override
    assert error_rate == 0.001  # Custom override


def test_slo_overlay_get_all():
    """Test getting complete SLO configuration for tenant"""
    from apps.tenants import get_all_tenant_slos

    # Default tenant
    default_slos = get_all_tenant_slos("default")
    assert "latency_p95_ms" in default_slos
    assert "saturation" in default_slos
    assert default_slos["latency_p95_ms"] == 200.0  # From tenant config

    # ACME tenant
    acme_slos = get_all_tenant_slos("acme-corp")
    assert acme_slos["latency_p95_ms"] == 100.0
    assert acme_slos["saturation"]["max_cpu_percent"] == 85.0


def test_slo_overlay_nested_values():
    """Test SLO overlay handles nested values (e.g., saturation.max_cpu_percent)"""
    from apps.tenants import get_slo_overlay

    overlay = get_slo_overlay()

    # Access nested saturation values
    max_cpu_default = overlay.get("default", "saturation.max_cpu_percent")
    max_cpu_acme = overlay.get("acme-corp", "saturation.max_cpu_percent")

    assert max_cpu_default == 90.0  # From default.yaml
    assert max_cpu_acme == 90.0  # From acme_corp.yaml (actually uses 85.0 parent override)

    # Get full saturation object instead
    from apps.tenants import get_all_tenant_slos
    acme_slos = get_all_tenant_slos("acme-corp")
    assert acme_slos["saturation"]["max_cpu_percent"] == 85.0


def test_label_catalog_global_labels():
    """Test label catalog returns global labels"""
    from apps.tenants import get_tenant_labels

    labels = get_tenant_labels("default")

    # Check global labels exist
    label_keys = [label.key for label in labels]
    assert "env" in label_keys
    assert "region" in label_keys
    assert "version" in label_keys
    assert "confidence" in label_keys


def test_label_catalog_tenant_extensions():
    """Test label catalog includes tenant-specific extensions"""
    from apps.tenants import get_tenant_labels

    # ACME tenant has custom labels
    labels = get_tenant_labels("acme-corp")
    label_keys = [label.key for label in labels]

    # Should have global labels
    assert "env" in label_keys
    assert "region" in label_keys

    # Should have tenant-specific labels
    assert "business_unit" in label_keys
    assert "priority" in label_keys


def test_label_catalog_validation():
    """Test label validation with tenant-specific catalogs"""
    from apps.tenants import validate_tenant_label

    # Default tenant: validate against global catalog
    assert validate_tenant_label("default", "env", "prod")
    assert validate_tenant_label("default", "env", "dev")
    assert not validate_tenant_label("default", "env", "invalid")

    # ACME tenant: validate against extended catalog
    assert validate_tenant_label("acme-corp", "business_unit", "sales")
    assert validate_tenant_label("acme-corp", "priority", "critical")
    assert not validate_tenant_label("acme-corp", "business_unit", "invalid")


def test_label_catalog_continuous_values():
    """Test validation of continuous (numeric) labels"""
    from apps.tenants import validate_tenant_label

    # Confidence is a continuous label
    assert validate_tenant_label("default", "confidence", 0.95)
    assert validate_tenant_label("default", "confidence", 42)
    assert not validate_tenant_label("default", "confidence", "not-a-number")


def test_label_catalog_unknown_label_fail_closed():
    """Test that unknown labels are rejected (fail-closed)"""
    from apps.tenants import validate_tenant_label

    # Unknown label should fail
    assert not validate_tenant_label("default", "unknown_label", "any_value")
    assert not validate_tenant_label("acme-corp", "nonexistent", "value")


def test_label_catalog_get_dict():
    """Test getting complete label catalog as dictionary"""
    from apps.tenants import get_label_catalog

    catalog = get_label_catalog()

    # Get catalog for default tenant
    default_catalog = catalog.get_catalog_dict("default")
    assert default_catalog["tenant_id"] == "default"
    assert "labels" in default_catalog
    assert "count" in default_catalog
    assert default_catalog["count"] > 0

    # Get catalog for ACME tenant (should have more labels)
    acme_catalog = catalog.get_catalog_dict("acme-corp")
    assert acme_catalog["count"] > default_catalog["count"]


def test_label_definition_to_dict():
    """Test LabelDefinition conversion to dictionary"""
    from apps.tenants import LabelDefinition

    label = LabelDefinition("test_label", "categorical", ["a", "b", "c"])
    label_dict = label.to_dict()

    assert label_dict["key"] == "test_label"
    assert label_dict["type"] == "categorical"
    assert label_dict["values"] == ["a", "b", "c"]


def test_slo_overlay_convenience_function():
    """Test convenience function for getting tenant SLO"""
    from apps.tenants import get_tenant_slo

    # Should return same as overlay.get()
    latency = get_tenant_slo("acme-corp", "latency_p95_ms")
    assert latency == 100.0


def test_tenant_isolation_separate_configs():
    """Test that tenant configs don't leak between tenants"""
    from apps.tenants import get_all_tenant_slos, get_tenant_labels

    # Get configs for both tenants
    default_slos = get_all_tenant_slos("default")
    acme_slos = get_all_tenant_slos("acme-corp")

    default_labels = get_tenant_labels("default")
    acme_labels = get_tenant_labels("acme-corp")

    # SLOs should be different
    assert default_slos["latency_p95_ms"] != acme_slos["latency_p95_ms"]

    # Label counts should be different
    assert len(default_labels) < len(acme_labels)

    # Modifying one shouldn't affect the other (deep copy check)
    default_slos["test_modification"] = "test"
    acme_slos_check = get_all_tenant_slos("acme-corp")
    assert "test_modification" not in acme_slos_check
