from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class BacklogSubmit(BaseModel):
    title: str
    reach: float = Field(ge=0)
    impact: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    effort: float = Field(gt=0)
    owner: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class BacklogItem(BacklogSubmit):
    id: str
    rice: float
    created_at: str

    @staticmethod
    def from_submit(payload: BacklogSubmit, identifier: str, rice: float) -> "BacklogItem":
        return BacklogItem(
            id=identifier,
            title=payload.title,
            reach=payload.reach,
            impact=payload.impact,
            confidence=payload.confidence,
            effort=payload.effort,
            owner=payload.owner,
            tags=payload.tags,
            rice=rice,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


__all__ = ["BacklogSubmit", "BacklogItem"]

