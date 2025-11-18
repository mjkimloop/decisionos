"""
Tenant Configuration Loader

Loads tenant-specific configurations with validation and fail-closed behavior.
"""
import os
import re
import yaml
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime


class TenantConfig:
    """Tenant configuration with validation"""

    def __init__(self, config: Dict[str, Any]):
        self.tenant_id = config["tenant_id"]
        self.name = config["name"]
        self.status = config["status"]
        self.created_at = config["created_at"]
        self.updated_at = config["updated_at"]

        self.limits = config.get("limits", {})
        self.clock_skew_ms = config.get("clock_skew_ms", 60000)
        self.slo_overlay = config.get("slo_overlay")
        self.label_overlay = config.get("label_overlay")
        self.billing = config.get("billing", {})
        self.contacts = config.get("contacts", {})
        self.metadata = config.get("metadata", {})

        self._validate()

    def _validate(self) -> None:
        """Validate tenant configuration (fail-closed)"""
        # Validate tenant_id format (alphanumeric + dash only)
        if not re.match(r'^[a-z0-9-]+$', self.tenant_id):
            raise ValueError(
                f"Invalid tenant_id '{self.tenant_id}': "
                "must contain only lowercase letters, numbers, and dashes"
            )

        # Validate status
        if self.status not in ["active", "suspended"]:
            raise ValueError(f"Invalid status '{self.status}': must be 'active' or 'suspended'")

        # Validate limits
        if "max_qps" in self.limits and self.limits["max_qps"] <= 0:
            raise ValueError("max_qps must be positive")

        if "max_storage_gb" in self.limits and self.limits["max_storage_gb"] <= 0:
            raise ValueError("max_storage_gb must be positive")

        # Validate clock skew
        if self.clock_skew_ms < 0:
            raise ValueError("clock_skew_ms cannot be negative")

    def is_active(self) -> bool:
        """Check if tenant is active"""
        return self.status == "active"

    def get_max_qps(self) -> Optional[int]:
        """Get maximum QPS limit"""
        return self.limits.get("max_qps")

    def get_clock_skew_ms(self) -> int:
        """Get clock skew tolerance"""
        return self.clock_skew_ms

    def get_slo_override(self, key: str) -> Optional[Any]:
        """Get SLO overlay value if exists"""
        if not self.slo_overlay:
            return None
        return self.slo_overlay.get(key)


class TenantRegistry:
    """Registry for tenant configurations with caching"""

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            config_dir = os.path.join(os.getcwd(), "configs", "tenants")

        self.config_dir = Path(config_dir)
        self._cache: Dict[str, TenantConfig] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Load all tenant configurations"""
        if not self.config_dir.exists():
            print(f"[WARN] Tenant config directory not found: {self.config_dir}")
            return

        for yaml_file in self.config_dir.glob("*.yaml"):
            if yaml_file.name == "schema.yaml":
                continue

            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                tenant_config = TenantConfig(config)
                self._cache[tenant_config.tenant_id] = tenant_config

            except Exception as e:
                print(f"[ERROR] Failed to load tenant config {yaml_file}: {e}")
                # Fail-closed: skip invalid configs
                continue

    def get(self, tenant_id: str) -> Optional[TenantConfig]:
        """Get tenant configuration by ID"""
        return self._cache.get(tenant_id)

    def require(self, tenant_id: str) -> TenantConfig:
        """Get tenant configuration, fail if not found"""
        config = self.get(tenant_id)
        if not config:
            raise ValueError(f"Tenant '{tenant_id}' not found in registry")

        if not config.is_active():
            raise ValueError(f"Tenant '{tenant_id}' is not active (status: {config.status})")

        return config

    def list_active(self) -> list[str]:
        """List all active tenant IDs"""
        return [
            tenant_id
            for tenant_id, config in self._cache.items()
            if config.is_active()
        ]

    def reload(self) -> None:
        """Reload all tenant configurations"""
        self._cache.clear()
        self._load_all()


# Global registry instance
_registry: Optional[TenantRegistry] = None


def get_registry() -> TenantRegistry:
    """Get global tenant registry (singleton)"""
    global _registry
    if _registry is None:
        _registry = TenantRegistry()
    return _registry


def validate_tenant_id(tenant_id: str) -> None:
    """Validate tenant_id exists and is active (fail-closed)"""
    registry = get_registry()
    registry.require(tenant_id)
