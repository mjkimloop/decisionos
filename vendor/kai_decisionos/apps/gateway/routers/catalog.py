from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from apps.catalog.models import CatalogField, CatalogItem, CatalogUpdate
from apps.catalog.registry import registry


router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


class CatalogFieldBody(BaseModel):
    name: str
    type: str
    description: str | None = None
    sensitivity: str = "internal"
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_model(self) -> CatalogField:
        return CatalogField(**self.model_dump())


class CatalogCreateBody(BaseModel):
    id: str
    name: str
    type: str = "dataset"
    domain: str | None = None
    description: str | None = None
    owner: str | None = None
    sensitivity: str = "internal"
    tags: List[str] = Field(default_factory=list)
    fields: List[CatalogFieldBody] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("/items", status_code=201)
def create_item(body: CatalogCreateBody):
    existing = registry.get(body.id)
    if existing:
        raise HTTPException(status_code=409, detail="catalog_id_exists")
    item = CatalogItem(
        id=body.id,
        name=body.name,
        type=body.type,
        domain=body.domain,
        description=body.description,
        owner=body.owner,
        sensitivity=body.sensitivity,
        tags=body.tags,
        fields=[field.to_model() for field in body.fields],
        metadata=body.metadata,
    )
    try:
        registry.add(item)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="catalog_id_exists") from exc
    return item.model_dump(mode="json")


@router.get("/items")
def list_items(sensitivity: str | None = None):
    items = registry.list(sensitivity=sensitivity)
    return [item.model_dump(mode="json") for item in items]


@router.get("/items/{item_id}")
def get_item(item_id: str):
    item = registry.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="catalog_not_found")
    return item.model_dump(mode="json")


@router.patch("/items/{item_id}")
def update_item(item_id: str, payload: CatalogUpdate):
    item = registry.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="catalog_not_found")
    updated = registry.update(item_id, payload)
    return updated.model_dump(mode="json")


@router.get("/assets")
def list_assets(
    type: str | None = Query(default=None, alias="type"),
    domain: str | None = None,
    tag: str | None = None,
    sensitivity: str | None = None,
):
    items = registry.list(asset_type=type, domain=domain, tag=tag, sensitivity=sensitivity)
    return {"items": [item.model_dump(mode="json") for item in items]}


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str):
    item = registry.get(dataset_id)
    if not item or item.type != "dataset":
        raise HTTPException(status_code=404, detail="dataset_not_found")
    return item.model_dump(mode="json")
