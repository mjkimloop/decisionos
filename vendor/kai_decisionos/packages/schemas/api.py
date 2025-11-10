from pydantic import BaseModel, Field, conint, confloat
from typing import Any, List, Dict, Optional


# 도메인 모델: Lead 입력 스키마
class Lead(BaseModel):
    """Lead 입력 데이터 모델"""
    org_id: str
    credit_score: conint(ge=0, le=850)  # type: ignore[valid-type]
    dti: confloat(ge=0, le=2)  # type: ignore[valid-type]
    income_verified: bool
    converted: Optional[int] = None


# 도메인 모델: Action 출력 스키마
class Action(BaseModel):
    """Decision action 출력 모델"""
    class_: str = Field(..., alias="class")
    reasons: List[str]
    confidence: float
    required_docs: Optional[List[str]] = []

    model_config = {"populate_by_name": True}


class DecisionRequest(BaseModel):
    org_id: str = Field(..., description="Organization identifier")
    payload: Dict[str, Any] = Field(..., description="Lead payload")


class DecisionResponse(BaseModel):
    """Decision API 응답 모델"""
    action: Action
    decision_id: str


class SimulateResponse(BaseModel):
    metrics: Dict[str, float]


class ExplainResponse(BaseModel):
    rules_applied: List[str]
    model_meta: Dict[str, Any]
    input_hash: str
    output_hash: str
    timestamp: str
    consent_snapshot: Optional[Dict[str, Any]] = None
