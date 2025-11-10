from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from apps.quality.metrics import compute_quality


router = APIRouter(prefix="/api/v1/quality", tags=["quality"])


class QualityBody(BaseModel):
    records: list[dict]
    keys: list[str]


@router.post("/metrics")
def quality_metrics(body: QualityBody):
    metrics = compute_quality(body.records, body.keys)
    return {"metrics": metrics}

