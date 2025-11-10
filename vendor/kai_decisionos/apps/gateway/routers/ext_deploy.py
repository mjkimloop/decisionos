from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from apps.ext.deployer import (
    install_extension,
    enable_extension,
    disable_extension,
    list_extensions,
)


router = APIRouter(prefix="/api/v1/ext", tags=["extensions"])


class InstallBody(BaseModel):
    org_id: str
    artifact_ref: str
    signature: str
    manifest: Optional[dict] = None
    channel: Optional[str] = None


@router.post("/install", status_code=201)
def install(body: InstallBody):
    try:
        install = install_extension(
            org_id=body.org_id,
            artifact_ref=body.artifact_ref,
            signature=body.signature,
            manifest=body.manifest,
            channel=body.channel,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="artifact_not_found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return install.model_dump()


class ToggleBody(BaseModel):
    org_id: str
    name: str
    version: Optional[str] = Field(None, description="Required for enable")


@router.post("/enable")
def enable(body: ToggleBody):
    try:
        install = enable_extension(body.org_id, body.name, body.version or "")
    except KeyError:
        raise HTTPException(status_code=404, detail="extension_not_installed")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return install.model_dump()


@router.post("/disable")
def disable(body: ToggleBody):
    try:
        install = disable_extension(body.org_id, body.name)
    except KeyError:
        raise HTTPException(status_code=404, detail="extension_not_installed")
    return install.model_dump()


@router.get("/list")
def list_installed(org_id: str = Query(..., alias="org_id")):
    installs = list_extensions(org_id)
    return [install.model_dump() for install in installs]


__all__ = ["router"]
