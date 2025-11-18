"""
Tenant-specific SLO Overlay System

Allows tenants to override global SLO defaults with custom thresholds.
"""
from typing import Dict, Optional, Any
from .config import get_registry, TenantConfig


class SLOOverlay:
    """
    SLO configuration with tenant-specific overrides.

    Global defaults can be overridden per-tenant via tenant config files.
    """

    def __init__(self, global_defaults: Optional[Dict[str, Any]] = None):
        """
        Initialize SLO overlay system.

        Args:
            global_defaults: Global SLO defaults (fallback values)
        """
        self.global_defaults = global_defaults or {
            "latency_p95_ms": 500.0,
            "latency_p99_ms": 1000.0,
            "error_rate_max": 0.05,
            "saturation": {
                "max_cpu_percent": 90.0,
                "max_mem_percent": 85.0,
                "max_qps": None,
            },
        }
        self.registry = get_registry()

    def get(self, tenant_id: str, key: str) -> Any:
        """
        Get SLO value for tenant with fallback to global default.

        Args:
            tenant_id: Tenant identifier
            key: SLO key (e.g., "latency_p95_ms", "error_rate_max")

        Returns:
            SLO value (tenant override or global default)
        """
        # Try to get tenant config
        config = self.registry.get(tenant_id)
        if config and config.slo_overlay:
            # Check if tenant has override for this key
            value = config.slo_overlay.get(key)
            if value is not None:
                return value

        # Fallback to global default
        return self._get_nested(self.global_defaults, key)

    def get_all(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get all SLO values for tenant (merged with global defaults).

        Args:
            tenant_id: Tenant identifier

        Returns:
            Complete SLO configuration for tenant
        """
        # Start with global defaults
        result = self.global_defaults.copy()

        # Try to get tenant config
        config = self.registry.get(tenant_id)
        if config and config.slo_overlay:
            # Merge tenant overrides (shallow merge)
            for key, value in config.slo_overlay.items():
                if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                    # Deep merge for nested dicts (e.g., saturation)
                    result[key] = {**result[key], **value}
                else:
                    result[key] = value

        return result

    def _get_nested(self, d: Dict[str, Any], key: str) -> Any:
        """Get nested dictionary value by dot notation"""
        if "." in key:
            parts = key.split(".", 1)
            if parts[0] in d and isinstance(d[parts[0]], dict):
                return self._get_nested(d[parts[0]], parts[1])
            return None
        return d.get(key)


# Global instance
_slo_overlay: Optional[SLOOverlay] = None


def get_slo_overlay() -> SLOOverlay:
    """Get global SLO overlay instance (singleton)"""
    global _slo_overlay
    if _slo_overlay is None:
        _slo_overlay = SLOOverlay()
    return _slo_overlay


def get_tenant_slo(tenant_id: str, key: str) -> Any:
    """
    Get SLO value for tenant (convenience function).

    Args:
        tenant_id: Tenant identifier
        key: SLO key

    Returns:
        SLO value for tenant
    """
    overlay = get_slo_overlay()
    return overlay.get(tenant_id, key)


def get_all_tenant_slos(tenant_id: str) -> Dict[str, Any]:
    """
    Get all SLO values for tenant (convenience function).

    Args:
        tenant_id: Tenant identifier

    Returns:
        Complete SLO configuration
    """
    overlay = get_slo_overlay()
    return overlay.get_all(tenant_id)
