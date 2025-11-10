from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.products.registry import registry
from apps.products.schema import ProductVersion
from apps.products.builder import build_manifest


router = APIRouter(prefix="/api/v1/products", tags=["products"])


class ProductRegisterBody(BaseModel):
    id: str
    name: str
    version: str
    description: str | None = None
    owner: str | None = None
    catalog_refs: list[str] = []
    definition: dict = {}


@router.post("/register", status_code=201)
def register_product(body: ProductRegisterBody):
    version = ProductVersion(
        version=body.version,
        description=body.description,
        owner=body.owner,
        catalog_refs=body.catalog_refs,
        definition=body.definition,
    )
    prod = registry.register(body.id, body.name, version)
    return prod.model_dump(mode="json")


@router.post("/{product_id}/publish")
def publish_product(product_id: str, version: str):
    try:
        ver = registry.publish(product_id, version)
    except KeyError:
        raise HTTPException(status_code=404, detail="product_not_found")
    return ver.model_dump(mode="json")


@router.post("/{product_id}/rollback")
def rollback_product(product_id: str):
    try:
        ver = registry.rollback(product_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="product_not_found")
    return ver.model_dump(mode="json")


@router.get("")
def list_products():
    return [product.model_dump(mode="json") for product in registry.list()]


@router.get("/{product_id}")
def product_detail(product_id: str):
    prod = registry.get(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="product_not_found")
    return prod.model_dump(mode="json")


@router.get("/{product_id}/manifest")
def product_manifest(product_id: str, version: str | None = None):
    prod = registry.get(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="product_not_found")
    ver = prod.versions[-1] if version is None else registry.get_version(product_id, version)
    manifest = build_manifest(
        {
            "id": product_id,
            "name": prod.name,
            "version": ver.version,
            "catalog_refs": ver.catalog_refs,
            "definition": ver.definition,
        }
    )
    return manifest
