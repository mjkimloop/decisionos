from __future__ import annotations

from sqlalchemy import insert

from .base import get_session
from .models import Decision as DecisionModel


def persist_decision(decision: dict):
    """결정 레코드를 DB에 저장(베타). 실패해도 예외를 전파하지 않음."""
    with get_session() as s:
        s.execute(
            insert(DecisionModel).values(
                id=decision.get("decision_id"),
                lead_id=None,
                contract=decision.get("contract"),
                klass=decision.get("class"),
                reasons=decision.get("reasons"),
                confidence=str(decision.get("confidence")),
                model_meta=decision.get("model_meta"),
                rules_version=decision.get("rules_version"),
            )
        )
        s.commit()

