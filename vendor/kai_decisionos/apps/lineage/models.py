from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from pydantic import BaseModel, Field


class LineageEdge(BaseModel):
    source_dataset: str
    target_dataset: str
    source_field: str | None = None
    target_field: str | None = None
    transformation: str | None = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def key(self) -> tuple[str, str, str | None, str | None]:
        return (
            self.source_dataset,
            self.target_dataset,
            self.source_field,
            self.target_field,
        )


__all__ = ["LineageEdge"]
