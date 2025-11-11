from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import time

labels_router = APIRouter()

_CACHE = {"seed": None, "ts": 0, "palette": None}

# Mock RBAC for now - will integrate with existing RBAC system
def require_scope(scope: str):
    def dependency():
        # In production, this would validate RBAC token
        return True
    return dependency

@labels_router.post("/admin/invalidate")
def invalidate(payload: Dict[str, Any], _=Depends(require_scope("ops:write"))):
    from .cards.aggregation import etag_seed
    scope = payload.get("scope")
    if scope != "labels":
        raise HTTPException(status_code=400, detail="unsupported scope")
    _CACHE.update({"seed": None, "ts": 0, "palette": None})
    return {"status":"ok"}

@labels_router.get("/cards/reason-trends/palette")
def palette(_=Depends(require_scope("ops:read"))):
    from .cards.aggregation import palette_with_desc, etag_seed
    seed = etag_seed()
    if _CACHE["seed"] != seed:
        _CACHE["palette"] = palette_with_desc()
        _CACHE["seed"] = seed
        _CACHE["ts"] = int(time.time())
    return {"seed": seed, "palette": _CACHE["palette"], "generated_at": _CACHE["ts"]}
