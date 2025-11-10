from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ExtensionManifest(BaseModel):
    name: str
    version: str
    type: str = "decision"
    entrypoint: str = "extension:handle"
    permissions: List[str] = Field(default_factory=list)
    runtime: str = "python-3.11"
    resources: Dict[str, Any] = Field(default_factory=dict)
    network: Dict[str, Any] = Field(default_factory=dict)
    secrets: List[str] = Field(default_factory=list)
    compat: Dict[str, Any] = Field(default_factory=dict)
    config: Dict[str, Any] = Field(default_factory=dict)


class ExtensionInstall(BaseModel):
    org_id: str
    artifact_ref: str
    manifest: ExtensionManifest
    channel: str = "dev"
    enabled: bool = False
    installed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    enabled_at: str | None = None


__all__ = ["ExtensionManifest", "ExtensionInstall"]
