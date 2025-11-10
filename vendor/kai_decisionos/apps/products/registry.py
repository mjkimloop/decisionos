from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Iterable, List, Tuple

from .schema import ProductSpec, ProductVersion
from .builder import build_manifest


class ProductRegistry:
    def __init__(self) -> None:
        self._versions: Dict[Tuple[str, str], ProductVersion] = {}

    def register(self, spec: ProductSpec) -> ProductVersion:
        key = (spec.name, spec.version)
        if key in self._versions:
            raise ValueError("product_version_exists")
        version = ProductVersion(name=spec.name, version=spec.version, spec=spec)
        self._versions[key] = version
        return version

    def publish(self, name: str, version: str) -> ProductVersion:
        key = (name, version)
        if key not in self._versions:
            raise KeyError("product_not_found")
        entry = self._versions[key]
        entry.status = "published"
        entry.published_at = datetime.now(timezone.utc)
        entry.manifest = build_manifest(entry)
        self._versions[key] = entry
        return entry

    def rollback(self, name: str, version: str) -> ProductVersion:
        key = (name, version)
        if key not in self._versions:
            raise KeyError("product_not_found")
        entry = self._versions[key]
        entry.status = "rolled_back"
        entry.manifest = None
        entry.published_at = None
        self._versions[key] = entry
        return entry

    def get(self, name: str, version: str) -> ProductVersion | None:
        return self._versions.get((name, version))

    def list(self, name: str | None = None) -> List[ProductVersion]:
        items = list(self._versions.values())
        if name:
            items = [item for item in items if item.name == name]
        return sorted(items, key=lambda item: (item.name, item.version))


registry = ProductRegistry()


__all__ = ["registry", "ProductRegistry"]
