from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from apps.lineage.collector import ingest, list_edges
from apps.lineage.graph import graph as lineage_graph, impact as lineage_impact
from apps.lineage.models import LineageEdge


router = APIRouter(prefix="/api/v1/lineage", tags=["lineage"])


class LineageIngestBody(BaseModel):
    dataset: str
    edges: List[LineageEdge]


@router.post("/edges", status_code=202)
def ingest_edges(body: LineageIngestBody):
    ingest(body.dataset, body.edges)
    return {"dataset": body.dataset, "ingested": len(body.edges)}


@router.get("/edges/{dataset}")
def get_edges(dataset: str):
    edges = list_edges(dataset)
    return {"dataset": dataset, "edges": [edge.model_dump(mode="json") for edge in edges]}


@router.get("/graph")
def get_graph(dataset: str, depth: int = Query(default=1, ge=0, le=5)):
    try:
        result = lineage_graph(dataset, depth=depth)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result


@router.get("/impact")
def get_impact(
    dataset: str,
    field: str | None = Query(default=None),
    depth: int = Query(default=3, ge=0, le=5),
):
    try:
        result = lineage_impact(dataset, field=field, depth=depth)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result


__all__ = ["router"]
