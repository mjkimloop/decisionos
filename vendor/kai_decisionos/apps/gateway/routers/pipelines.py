from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from apps.pipelines.service import run_pipeline


router = APIRouter(prefix="/api/v1/pipelines", tags=["pipelines"])


class PipelineRequest(BaseModel):
    records: list[dict]


@router.post("/run")
def run(body: PipelineRequest):
    output = run_pipeline(body.records)
    return {"n": len(output), "records": output}

