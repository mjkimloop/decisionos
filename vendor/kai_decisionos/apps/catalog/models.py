from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class CatalogField(BaseModel):
    name: str
    type: str
    description: str | None = None
    sensitivity: str = "internal"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CatalogItem(BaseModel):
    id: str
    name: str
    type: str = "dataset"
    domain: str | None = None
    description: str | None = None
    owner: str | None = None
    sensitivity: str = "internal"
    tags: List[str] = Field(default_factory=list)
    fields: List[CatalogField] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CatalogUpdate(BaseModel):
    description: str | None = None
    owner: str | None = None
    sensitivity: str | None = None
    tags: List[str] | None = None
    type: str | None = None
    domain: str | None = None
    fields: List[CatalogField] | None = None
    metadata: Dict[str, Any] | None = None


__all__ = ["CatalogItem", "CatalogUpdate", "CatalogField"]
