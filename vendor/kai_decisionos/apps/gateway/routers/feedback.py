from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from apps.feedback.models import FeedbackSubmit
from apps.feedback.store import add_feedback, list_feedback
from apps.feedback.classifier import aggregate_feedback


router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


@router.post("/nps", status_code=201)
def submit_feedback(payload: FeedbackSubmit):
    entry = add_feedback(payload)
    return entry.model_dump(mode="json")


@router.get("/stats")
def feedback_stats():
    feedback = list_feedback()
    ratings = [entry.rating for entry in feedback]
    agg = aggregate_feedback(ratings)
    return {"n": len(ratings), **agg}

