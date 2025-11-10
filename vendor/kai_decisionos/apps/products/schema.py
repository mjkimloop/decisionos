from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Dict, List

from pydantic import BaseModel, Field, validator


class PublishTarget(BaseModel):
    kind: str
    params: Dict[str, Any] = Field(default_factory=dict)


class ProductSpec(BaseModel):
    name: str
    version: str
    owner: str
    input_datasets: List[str] = Field(default_factory=list)
    transforms: List[str] = Field(default_factory=list)
    slas: Dict[str, Any] = Field(default_factory=dict)
    publish: List[PublishTarget] = Field(default_factory=list)
    contracts: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("version")
    def validate_version(cls, value: str) -> str:
        if not value:
            raise ValueError("version_required")
        if value.count(".") < 1:
            raise ValueError("version_must_follow_semver_like_pattern")
        return value

    def fingerprint(self) -> str:
        digest = sha256(str(self.model_dump(mode="json", exclude_none=True, exclude={"metadata"})).encode("utf-8")).hexdigest()
        return digest


class ProductVersion(BaseModel):
    name: str
    version: str
    status: str = "draft"
    spec: ProductSpec
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    published_at: datetime | None = None
    manifest: Dict[str, Any] | None = None

    def key(self) -> tuple[str, str]:
        return (self.name, self.version)


__all__ = ["ProductSpec", "ProductVersion", "PublishTarget"]
