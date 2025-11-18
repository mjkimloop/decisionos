"""
Tenant Context — Propagation across HTTP/CLI/ENV

Provides unified tenant context extraction and validation.
"""
import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class TenantContext:
    """
    Tenant context with validation.

    Immutable context object passed through request lifecycle.
    """
    tenant_id: str

    def __post_init__(self):
        """Validate tenant_id after initialization"""
        if not self.tenant_id:
            raise TenantMissing("tenant_id is required")

        # Import here to avoid circular dependency
        from apps.tenants import validate_tenant_id
        try:
            validate_tenant_id(self.tenant_id)
        except ValueError as e:
            raise TenantUnknown(f"Unknown or inactive tenant: {self.tenant_id}") from e

    @classmethod
    def from_env(cls, var_name: str = "DECISIONOS_TENANT") -> "TenantContext":
        """
        Create TenantContext from environment variable.

        Args:
            var_name: Environment variable name (default: DECISIONOS_TENANT)

        Returns:
            TenantContext instance

        Raises:
            TenantMissing: If environment variable is not set
            TenantUnknown: If tenant is invalid/inactive
        """
        tenant_id = os.environ.get(var_name)
        if not tenant_id:
            raise TenantMissing(f"Environment variable {var_name} not set")
        return cls(tenant_id=tenant_id)

    @classmethod
    def from_header(cls, headers: dict, header_name: str = "X-DecisionOS-Tenant") -> "TenantContext":
        """
        Create TenantContext from HTTP header.

        Args:
            headers: Request headers dict
            header_name: Header name (default: X-DecisionOS-Tenant)

        Returns:
            TenantContext instance

        Raises:
            TenantMissing: If header is not present
            TenantUnknown: If tenant is invalid/inactive
        """
        tenant_id = headers.get(header_name)
        if not tenant_id:
            raise TenantMissing(f"Header {header_name} not present")
        return cls(tenant_id=tenant_id)

    @classmethod
    def from_query(cls, query_params: dict, param_name: str = "tenant") -> "TenantContext":
        """
        Create TenantContext from query parameter.

        Args:
            query_params: Query parameters dict
            param_name: Parameter name (default: tenant)

        Returns:
            TenantContext instance

        Raises:
            TenantMissing: If parameter is not present
            TenantUnknown: If tenant is invalid/inactive
        """
        tenant_id = query_params.get(param_name)
        if not tenant_id:
            raise TenantMissing(f"Query parameter {param_name} not present")
        return cls(tenant_id=tenant_id)

    def to_header(self, header_name: str = "X-DecisionOS-Tenant") -> dict:
        """
        Convert to HTTP header dict.

        Args:
            header_name: Header name (default: X-DecisionOS-Tenant)

        Returns:
            Dict with tenant header
        """
        return {header_name: self.tenant_id}

    def to_env(self, var_name: str = "DECISIONOS_TENANT") -> dict:
        """
        Convert to environment variable dict.

        Args:
            var_name: Variable name (default: DECISIONOS_TENANT)

        Returns:
            Dict with tenant environment variable
        """
        return {var_name: self.tenant_id}


class TenantMissing(ValueError):
    """Raised when tenant is required but not provided (fail-closed)"""
    def __init__(self, message: str):
        super().__init__(message)
        self.reason_code = "tenant.missing"


class TenantUnknown(ValueError):
    """Raised when tenant is invalid or inactive (fail-closed)"""
    def __init__(self, message: str):
        super().__init__(message)
        self.reason_code = "tenant.unknown"


def require_tenant_context(
    headers: Optional[dict] = None,
    query: Optional[dict] = None,
    env_var: str = "DECISIONOS_TENANT"
) -> TenantContext:
    """
    Extract and validate tenant context from multiple sources (fail-closed).

    Priority: headers > query > environment

    Args:
        headers: HTTP headers dict
        query: Query parameters dict
        env_var: Environment variable name

    Returns:
        TenantContext instance

    Raises:
        TenantMissing: If tenant not found in any source
        TenantUnknown: If tenant is invalid/inactive
    """
    # Try headers first
    if headers:
        try:
            return TenantContext.from_header(headers)
        except TenantMissing:
            pass

    # Try query parameters
    if query:
        try:
            return TenantContext.from_query(query)
        except TenantMissing:
            pass

    # Try environment
    try:
        return TenantContext.from_env(env_var)
    except TenantMissing:
        pass

    # Nothing found - fail closed
    raise TenantMissing("Tenant not found in headers, query, or environment")
