from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Iterable, List, Sequence

from .models import CatalogItem, CatalogUpdate
import apps.catalog.indexer as indexer


class CatalogRegistry:
    def __init__(self) -> None:
        self._items: Dict[str, CatalogItem] = {}

    def add(self, item: CatalogItem) -> CatalogItem:
        if item.id in self._items:
            raise ValueError(f"catalog_item_exists:{item.id}")
        now = datetime.now(timezone.utc)
        item.created_at = now
        item.updated_at = now
        self._items[item.id] = item
        indexer.update(item)
        return item

    def get(self, item_id: str) -> CatalogItem | None:
        return self._items.get(item_id)

    def list(
        self,
        asset_type: str | None = None,
        domain: str | None = None,
        tag: str | None = None,
        sensitivity: Sequence[str] | str | None = None,
    ) -> List[CatalogItem]:
        items = list(self._items.values())
        if asset_type:
            items = [it for it in items if it.type == asset_type]
        if domain:
            items = [it for it in items if it.domain == domain]
        if tag:
            items = [it for it in items if tag in it.tags]
        if sensitivity:
            allowed = (
                {sensitivity}
                if isinstance(sensitivity, str)
                else set(sensitivity)
            )
            items = [it for it in items if it.sensitivity in allowed]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def update(self, item_id: str, payload: CatalogUpdate) -> CatalogItem:
        item = self._items[item_id]
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        item.updated_at = datetime.now(timezone.utc)
        indexer.update(item)
        return item

    def upsert_many(self, items: Iterable[CatalogItem]) -> None:
        for item in items:
            if item.id in self._items:
                self.update(item.id, CatalogUpdate(**item.model_dump()))
            else:
                self.add(item)


registry = CatalogRegistry()


__all__ = ["registry", "CatalogRegistry"]
