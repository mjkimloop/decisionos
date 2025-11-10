from __future__ import annotations

from typing import Dict, Any


def build_manifest(product: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": product["id"],
        "name": product["name"],
        "version": product.get("version"),
        "catalog_refs": product.get("catalog_refs", []),
        "definition": product.get("definition", {}),
    }


__all__ = ["build_manifest"]
