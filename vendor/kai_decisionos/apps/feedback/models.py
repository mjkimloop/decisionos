from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class FeedbackSubmit(BaseModel):
    rating: int = Field(ge=0, le=10)
    comment: Optional[str] = None
    user_id: Optional[str] = None
    channel: Optional[str] = Field(default="web")


class FeedbackEntry(FeedbackSubmit):
    id: str
    bucket: str
    created_at: str

    @staticmethod
    def from_submit(payload: FeedbackSubmit, identifier: str) -> "FeedbackEntry":
        from .classifier import classify_feedback  # local import to avoid cycle

        bucket = classify_feedback(payload.rating)
        return FeedbackEntry(
            id=identifier,
            rating=payload.rating,
            comment=payload.comment,
            user_id=payload.user_id,
            channel=payload.channel,
            bucket=bucket,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


__all__ = ["FeedbackSubmit", "FeedbackEntry"]

