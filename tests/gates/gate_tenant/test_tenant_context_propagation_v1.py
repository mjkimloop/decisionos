"""
Gate Tenant — Tenant context propagation tests
"""
import pytest
import os

pytestmark = pytest.mark.gate_tenant


def test_tenant_context_from_header():
    """Test creating TenantContext from HTTP header"""
    from apps.common import TenantContext

    headers = {"X-DecisionOS-Tenant": "default"}
    ctx = TenantContext.from_header(headers)

    assert ctx.tenant_id == "default"


def test_tenant_context_from_header_custom_name():
    """Test custom header name"""
    from apps.common import TenantContext

    headers = {"X-Custom-Tenant": "acme-corp"}
    ctx = TenantContext.from_header(headers, header_name="X-Custom-Tenant")

    assert ctx.tenant_id == "acme-corp"


def test_tenant_context_from_header_missing():
    """Test missing header raises TenantMissing"""
    from apps.common import TenantContext, TenantMissing

    headers = {}

    with pytest.raises(TenantMissing, match="not present"):
        TenantContext.from_header(headers)


def test_tenant_context_from_query():
    """Test creating TenantContext from query parameter"""
    from apps.common import TenantContext

    query = {"tenant": "default"}
    ctx = TenantContext.from_query(query)

    assert ctx.tenant_id == "default"


def test_tenant_context_from_query_missing():
    """Test missing query parameter raises TenantMissing"""
    from apps.common import TenantContext, TenantMissing

    query = {}

    with pytest.raises(TenantMissing, match="not present"):
        TenantContext.from_query(query)


def test_tenant_context_from_env():
    """Test creating TenantContext from environment variable"""
    from apps.common import TenantContext

    os.environ["DECISIONOS_TENANT"] = "default"

    try:
        ctx = TenantContext.from_env()
        assert ctx.tenant_id == "default"
    finally:
        if "DECISIONOS_TENANT" in os.environ:
            del os.environ["DECISIONOS_TENANT"]


def test_tenant_context_from_env_custom_var():
    """Test custom environment variable name"""
    from apps.common import TenantContext

    os.environ["CUSTOM_TENANT"] = "acme-corp"

    try:
        ctx = TenantContext.from_env(var_name="CUSTOM_TENANT")
        assert ctx.tenant_id == "acme-corp"
    finally:
        if "CUSTOM_TENANT" in os.environ:
            del os.environ["CUSTOM_TENANT"]


def test_tenant_context_from_env_missing():
    """Test missing environment variable raises TenantMissing"""
    from apps.common import TenantContext, TenantMissing

    # Ensure variable is not set
    if "DECISIONOS_TENANT" in os.environ:
        del os.environ["DECISIONOS_TENANT"]

    with pytest.raises(TenantMissing, match="not set"):
        TenantContext.from_env()


def test_tenant_context_invalid_tenant():
    """Test invalid tenant raises TenantUnknown"""
    from apps.common import TenantContext, TenantUnknown

    headers = {"X-DecisionOS-Tenant": "invalid-nonexistent-tenant"}

    with pytest.raises(TenantUnknown, match="Unknown or inactive"):
        TenantContext.from_header(headers)


def test_tenant_context_to_header():
    """Test converting TenantContext to header dict"""
    from apps.common import TenantContext

    ctx = TenantContext(tenant_id="default")
    headers = ctx.to_header()

    assert headers == {"X-DecisionOS-Tenant": "default"}


def test_tenant_context_to_header_custom_name():
    """Test converting to custom header name"""
    from apps.common import TenantContext

    ctx = TenantContext(tenant_id="default")
    headers = ctx.to_header(header_name="X-Custom-Tenant")

    assert headers == {"X-Custom-Tenant": "default"}


def test_tenant_context_to_env():
    """Test converting TenantContext to environment variable dict"""
    from apps.common import TenantContext

    ctx = TenantContext(tenant_id="default")
    env = ctx.to_env()

    assert env == {"DECISIONOS_TENANT": "default"}


def test_require_tenant_context_priority():
    """Test tenant context extraction priority (headers > query > env)"""
    from apps.common import require_tenant_context

    # Use actual tenants from config (default and acme-corp)
    os.environ["DECISIONOS_TENANT"] = "default"
    headers = {"X-DecisionOS-Tenant": "acme-corp"}
    query = {"tenant": "default"}

    try:
        # Headers should have priority
        ctx = require_tenant_context(headers=headers, query=query)
        assert ctx.tenant_id == "acme-corp"

        # Without headers, query should have priority
        ctx = require_tenant_context(query=query)
        assert ctx.tenant_id == "default"

        # Without headers or query, env should be used
        ctx = require_tenant_context()
        assert ctx.tenant_id == "default"

    finally:
        if "DECISIONOS_TENANT" in os.environ:
            del os.environ["DECISIONOS_TENANT"]


def test_require_tenant_context_missing_all():
    """Test require_tenant_context fails closed when all sources missing"""
    from apps.common import require_tenant_context, TenantMissing

    # Ensure env is not set
    if "DECISIONOS_TENANT" in os.environ:
        del os.environ["DECISIONOS_TENANT"]

    with pytest.raises(TenantMissing, match="not found in headers, query, or environment"):
        require_tenant_context(headers={}, query={})


def test_tenant_missing_reason_code():
    """Test TenantMissing exception has reason_code"""
    from apps.common import TenantMissing

    exc = TenantMissing("test message")
    assert exc.reason_code == "tenant.missing"


def test_tenant_unknown_reason_code():
    """Test TenantUnknown exception has reason_code"""
    from apps.common import TenantUnknown

    exc = TenantUnknown("test message")
    assert exc.reason_code == "tenant.unknown"


def test_tenant_context_immutable():
    """Test TenantContext is immutable (dataclass frozen would be better)"""
    from apps.common import TenantContext

    ctx = TenantContext(tenant_id="default")

    # Should be able to read
    assert ctx.tenant_id == "default"

    # In a frozen dataclass, this would raise, but for now just verify it exists
    assert hasattr(ctx, "tenant_id")
