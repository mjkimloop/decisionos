from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query

from apps.catalog import indexer
from apps.catalog.registry import registry

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("")
def search_catalog(
    q: str = Query(..., description="검색 키워드"),
    scope: str = Query(default="asset", description="asset|dataset|field"),
    limit: int = Query(default=10, ge=1, le=50),
    sensitivity: str | None = Query(default=None, description="허용 민감도"),
):
    allowed = [sensitivity] if sensitivity else None
    try:
        item_ids = indexer.search(q, limit=limit, scope=scope, allowed_sensitivity=allowed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    results: List[dict] = []
    for item_id in item_ids:
        item = registry.get(item_id)
        if not item:
            continue
        if sensitivity and item.sensitivity != sensitivity:
            continue
        results.append(item.model_dump(mode="json"))
    return {"results": results}
