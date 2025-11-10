from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field, field_validator


class PackMeta(BaseModel):
    name: str
    version: str = Field(pattern=r"^v\d+\.\d+\.\d+$", description="semantic version")
    domain: str
    owner: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    tags: Dict[str, str] = Field(default_factory=dict)


class PackComponent(BaseModel):
    id: str
    kind: Literal["rule", "model", "dataset", "policy", "hook", "route", "schema"]
    path: str
    config: Dict[str, Any] = Field(default_factory=dict)


class PackSpec(BaseModel):
    meta: PackMeta
    contracts: List[str] = Field(default_factory=list)
    rulesets: List[str] = Field(default_factory=list)
    datasets: List[str] = Field(default_factory=list)
    simulators: List[str] = Field(default_factory=list)
    components: List[PackComponent] = Field(default_factory=list)
    checklist: List[str] = Field(default_factory=list)

    @field_validator("contracts", "rulesets", "datasets", "simulators", mode="after")
    @classmethod
    def ensure_unique(cls, value: List[str]) -> List[str]:
        seen: set[str] = set()
        deduped: List[str] = []
        for item in value:
            if item not in seen:
                seen.add(item)
                deduped.append(item)
        return deduped

    def identifier(self) -> str:
        return f"{self.meta.name}:{self.meta.version}"


class LintIssue(BaseModel):
    level: Literal["error", "warning", "info"]
    message: str
    subject: Optional[str] = None


__all__ = ["PackMeta", "PackComponent", "PackSpec", "LintIssue"]

