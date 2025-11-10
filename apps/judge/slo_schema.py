"""
apps/judge/slo_schema.py

SLO-as-Code 스키마 정의 (Pydantic)
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class SLOBudget(BaseModel):
    """예산 정책"""

    allow_levels: List[str] = Field(
        default_factory=lambda: ["ok", "warn"]
    )  # "exceeded" 금지
    max_spent: Optional[float] = None  # 선택: 절대 금액 상한


class SLOQuota(BaseModel):
    """할당량 정책"""

    forbid_actions: Dict[str, List[str]] = Field(
        default_factory=dict
    )  # {"tokens": ["deny"]}


class SLOAnomaly(BaseModel):
    """이상 탐지 정책"""

    allow_spike: bool = False


class SLOWitness(BaseModel):
    """Witness 검증 정책"""

    require_csv_sha256: bool = True
    require_signature: bool = True
    min_rows: int = 1


class SLOIntegrity(BaseModel):
    """무결성 검증 정책"""

    require_signature: bool = True


class SLOQuorum(BaseModel):
    """쿼럼 정책"""

    k: int = 2
    n: int = 3
    fail_closed_on_degrade: bool = True


class SLOSpec(BaseModel):
    """전체 SLO 스펙"""

    version: str = "v1"
    budget: SLOBudget = SLOBudget()
    quota: SLOQuota = SLOQuota()
    anomaly: SLOAnomaly = SLOAnomaly()
    witness: SLOWitness = SLOWitness()
    integrity: SLOIntegrity = SLOIntegrity()
    quorum: SLOQuorum = SLOQuorum()
