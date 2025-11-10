from __future__ import annotations

from fastapi import APIRouter

from apps.lineage.collector import ingest, list_edges
from apps.lineage.graph import graph


router = APIRouter(prefix="/api/v1/lineage", tags=["lineage"])


@router.post("/edges", status_code=201)
def collect_edges(payload: dict):
    edges = payload.get("edges", [])
    count = ingest(edges)
    return {"ingested": count}


@router.get("/edges")
def get_edges():
    return {"edges": [edge.__dict__ for edge in list_edges()]}


@router.get("/graph")
def lineage_graph(node: str, limit: int | None = None):
    return {
        "node": node,
        "upstream": graph.upstream(node, limit=limit),
        "downstream": graph.downstream(node, limit=limit),
    }


@router.get("/impact")
def lineage_impact(node: str, limit: int | None = None):
    return {"node": node, "impact": graph.impact(node, limit=limit)}
