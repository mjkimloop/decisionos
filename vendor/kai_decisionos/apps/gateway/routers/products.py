from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from apps.products.registry import registry
from apps.products.schema import ProductSpec, ProductVersion


router = APIRouter(prefix="/api/v1/products", tags=["products"])


class PublishBody(BaseModel):
    name: str
    version: str


class RollbackBody(BaseModel):
    name: str
    version: str


@router.post("/register", status_code=201)
def register_product(spec: ProductSpec):
    try:
        version = registry.register(spec)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return _serialize(version)


@router.post("/publish")
def publish_product(body: PublishBody):
    try:
        version = registry.publish(body.name, body.version)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize(version)


@router.post("/rollback")
def rollback_product(body: RollbackBody):
    try:
        version = registry.rollback(body.name, body.version)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize(version)


@router.get("/list")
def list_products(name: str | None = Query(default=None)):
    items = registry.list(name=name)
    return {"products": [_serialize(item) for item in items]}


def _serialize(version: ProductVersion) -> dict[str, Any]:
    data = version.model_dump(mode="json")
    return data


__all__ = ["router"]
