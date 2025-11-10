from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.connectors.sdk import registry
from apps.connectors import BOOTSTRAPPED

AVAILABLE_CONNECTORS = BOOTSTRAPPED


router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])


class ConnectorCreate(BaseModel):
    name: str
    params: dict = {}


@router.get("")
def list_connectors():
    return registry.list()


@router.post("/test")
def test_connector(body: ConnectorCreate):
    try:
        connector = registry.create(body.name, **body.params)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    sample = connector.fetch(limit=1)
    return {"name": body.name, "sample": sample}
