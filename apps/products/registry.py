from __future__ import annotations

from typing import Dict, List

from .schema import DataProduct, ProductVersion


class ProductRegistry:
    def __init__(self) -> None:
        self._products: Dict[str, DataProduct] = {}

    def register(self, product_id: str, name: str, version: ProductVersion) -> DataProduct:
        prod = self._products.get(product_id)
        if not prod:
            prod = DataProduct(id=product_id, name=name, versions=[version])
            self._products[product_id] = prod
        else:
            prod.name = name or prod.name
            prod.versions.append(version)
        return prod

    def publish(self, product_id: str, version: str) -> ProductVersion:
        prod = self._products[product_id]
        for ver in prod.versions:
            if ver.version == version:
                ver.status = "published"
            else:
                if ver.status == "published":
                    ver.status = "archived"
        return self.get_version(product_id, version)

    def rollback(self, product_id: str) -> ProductVersion:
        prod = self._products[product_id]
        if len(prod.versions) < 2:
            return prod.versions[-1]
        prod.versions.pop()
        prod.versions[-1].status = "published"
        return prod.versions[-1]

    def list(self) -> List[DataProduct]:
        return list(self._products.values())

    def get(self, product_id: str) -> DataProduct | None:
        return self._products.get(product_id)

    def get_version(self, product_id: str, version: str) -> ProductVersion:
        prod = self._products[product_id]
        for ver in prod.versions:
            if ver.version == version:
                return ver
        raise KeyError("version_not_found")


registry = ProductRegistry()


__all__ = ["registry", "ProductRegistry"]
