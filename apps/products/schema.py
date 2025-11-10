from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from pydantic import BaseModel, Field


class ProductVersion(BaseModel):
    version: str
    status: str = "draft"
    description: str | None = None
    owner: str | None = None
    catalog_refs: List[str] = Field(default_factory=list)
    definition: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DataProduct(BaseModel):
    id: str
    name: str
    versions: List[ProductVersion] = Field(default_factory=list)


__all__ = ["DataProduct", "ProductVersion"]
