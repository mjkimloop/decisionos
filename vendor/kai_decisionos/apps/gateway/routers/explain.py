from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from packages.schemas.api import ExplainResponse
from apps.executor.pipeline import explain as do_explain
from apps.policy.hooks.purpose import (
    PurposeBindingError,
    attach_consent_snapshot,
    enforce_purpose_binding,
)

router = APIRouter()


def auth_dep():
    return None


@router.get("/api/v1/explain/{decision_id}", response_model=ExplainResponse)
def explain(
    decision_id: str,
    subject_id: Optional[str] = Query(None, description="Subject identifier for consent binding"),
    purpose: Optional[str] = Query("explain", description="Purpose binding identifier"),
    scope: Optional[str] = Query(None, description="Comma separated scope entries"),
    _: None = Depends(auth_dep),
):
    try:
        data = do_explain(decision_id)
        if subject_id:
            scope_list = [item.strip() for item in (scope or "").split(",") if item.strip()]
            try:
                enforce_purpose_binding(
                    subject_id,
                    purpose=purpose or "explain",
                    scope=scope_list or ["explain"],
                    require_consent=True,
                )
            except PurposeBindingError as exc:
                raise HTTPException(status_code=403, detail={"error": exc.reason, **exc.detail}) from exc
            attach_consent_snapshot(data, subject_id, purpose=purpose or "explain")
        return data
    except KeyError:
        raise HTTPException(status_code=404, detail="decision_id not found")
