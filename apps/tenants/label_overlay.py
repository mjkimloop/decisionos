"""
Tenant-specific Label Catalog Overlay System

Allows tenants to extend global label catalogs with custom labels.
"""
from typing import Dict, List, Optional, Any
from .config import get_registry, TenantConfig


class LabelDefinition:
    """Label definition with type and optional allowed values"""

    def __init__(self, key: str, label_type: str, values: Optional[List[str]] = None):
        self.key = key
        self.label_type = label_type  # "categorical" or "continuous"
        self.values = values or []

    def validate(self, value: Any) -> bool:
        """Validate label value against definition"""
        if self.label_type == "categorical":
            return value in self.values
        elif self.label_type == "continuous":
            # Continuous values: any numeric value is allowed
            return isinstance(value, (int, float))
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        result = {"key": self.key, "type": self.label_type}
        if self.values:
            result["values"] = self.values
        return result


class LabelCatalog:
    """
    Label catalog with tenant-specific extensions.

    Global labels can be extended per-tenant via tenant config files.
    """

    def __init__(self, global_labels: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize label catalog.

        Args:
            global_labels: Global label definitions
        """
        # Default global labels
        self.global_labels = [
            LabelDefinition("env", "categorical", ["dev", "staging", "prod"]),
            LabelDefinition("region", "categorical", ["us-east-1", "us-west-2", "eu-west-1"]),
            LabelDefinition("version", "categorical", []),
            LabelDefinition("experiment_id", "categorical", []),
            LabelDefinition("confidence", "continuous"),
        ]

        # Override with provided global labels if any
        if global_labels:
            self.global_labels = [
                LabelDefinition(l["key"], l["type"], l.get("values"))
                for l in global_labels
            ]

        self.registry = get_registry()

    def get_labels(self, tenant_id: str) -> List[LabelDefinition]:
        """
        Get all label definitions for tenant (global + tenant-specific).

        Args:
            tenant_id: Tenant identifier

        Returns:
            List of label definitions
        """
        # Start with global labels
        labels = {label.key: label for label in self.global_labels}

        # Try to get tenant config
        config = self.registry.get(tenant_id)
        if config and config.label_overlay:
            # Add tenant-specific labels
            tenant_labels = config.label_overlay.get("additional_labels", [])
            for label_def in tenant_labels:
                key = label_def["key"]
                label_type = label_def["type"]
                values = label_def.get("values", [])
                labels[key] = LabelDefinition(key, label_type, values)

        return list(labels.values())

    def get_label(self, tenant_id: str, key: str) -> Optional[LabelDefinition]:
        """
        Get specific label definition for tenant.

        Args:
            tenant_id: Tenant identifier
            key: Label key

        Returns:
            Label definition or None if not found
        """
        labels = self.get_labels(tenant_id)
        for label in labels:
            if label.key == key:
                return label
        return None

    def validate_label(self, tenant_id: str, key: str, value: Any) -> bool:
        """
        Validate label value for tenant.

        Args:
            tenant_id: Tenant identifier
            key: Label key
            value: Label value

        Returns:
            True if valid, False otherwise
        """
        label_def = self.get_label(tenant_id, key)
        if not label_def:
            # Unknown label: fail-closed
            return False
        return label_def.validate(value)

    def get_catalog_dict(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get complete label catalog as dictionary for tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Dictionary representation of label catalog
        """
        labels = self.get_labels(tenant_id)
        return {
            "tenant_id": tenant_id,
            "labels": [label.to_dict() for label in labels],
            "count": len(labels),
        }


# Global instance
_label_catalog: Optional[LabelCatalog] = None


def get_label_catalog() -> LabelCatalog:
    """Get global label catalog instance (singleton)"""
    global _label_catalog
    if _label_catalog is None:
        _label_catalog = LabelCatalog()
    return _label_catalog


def get_tenant_labels(tenant_id: str) -> List[LabelDefinition]:
    """
    Get all label definitions for tenant (convenience function).

    Args:
        tenant_id: Tenant identifier

    Returns:
        List of label definitions
    """
    catalog = get_label_catalog()
    return catalog.get_labels(tenant_id)


def validate_tenant_label(tenant_id: str, key: str, value: Any) -> bool:
    """
    Validate label value for tenant (convenience function).

    Args:
        tenant_id: Tenant identifier
        key: Label key
        value: Label value

    Returns:
        True if valid, False otherwise
    """
    catalog = get_label_catalog()
    return catalog.validate_label(tenant_id, key, value)
