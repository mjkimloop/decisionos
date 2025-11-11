from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

router = APIRouter()

# Mock RBAC for now - will integrate with existing RBAC system
def require_scope(scope: str):
    def dependency():
        # In production, this would validate RBAC token
        return True
    return dependency

class AggregateReq(BaseModel):
    reasons: List[str] = Field(default_factory=list)
    top: int = 5

@router.get("/cards/reason-trends/palette")
def get_palette(_=Depends(require_scope("ops:read"))):
    from .cards.aggregation import palette_with_desc, etag_seed
    return {"seed": etag_seed(), "palette": palette_with_desc()}

@router.post("/cards/reason-trends")
def post_trends(req: AggregateReq, _=Depends(require_scope("ops:read"))):
    from .cards.aggregation import palette_with_desc, aggregate_reasons, label_catalog_hash
    if req.top < 1 or req.top > 50:
        raise HTTPException(status_code=400, detail="top must be 1..50")
    agg = aggregate_reasons(req.reasons, top=req.top)
    return {
        "catalog_sha": label_catalog_hash(),
        "palette": palette_with_desc(),
        **agg
    }
