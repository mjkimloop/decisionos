"""
apps/judge/slo_schema.py

SLO-as-Code 스키마 정의 (Pydantic)
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class SLOBudget(BaseModel):
    """예산 조건"""

    allow_levels: List[str] = Field(
        default_factory=lambda: ["ok", "warn"]
    )  # "exceeded" 허용 여부
    max_spent: Optional[float] = None  # 초과: 총 예산 한도


class SLOQuota(BaseModel):
    """쿼터 조건"""

    forbid_actions: Dict[str, List[str]] = Field(
        default_factory=dict
    )  # {"tokens": ["deny"]}


class SLOAnomaly(BaseModel):
    """이상 탐지 조건"""

    allow_spike: bool = False


class SLOWitness(BaseModel):
    """Witness 스펙 조건"""

    require_csv_sha256: bool = True
    require_signature: bool = True
    min_rows: int = 1


class SLOIntegrity(BaseModel):
    """무결성 조건"""

    require_signature: bool = True


class SLOLatency(BaseModel):
    """지연 시간 조건"""

    max_p95_ms: Optional[int] = None
    max_p99_ms: Optional[int] = None


class SLOError(BaseModel):
    """오류율 조건"""

    max_error_rate: Optional[float] = None


class SLOJudgeInfraLatency(BaseModel):
    max_p95_ms: Optional[int] = None
    max_p99_ms: Optional[int] = None


class SLOJudgeInfraAvailability(BaseModel):
    min_availability: Optional[float] = None


class SLOJudgeInfraSignature(BaseModel):
    max_sig_error_rate: Optional[float] = None


class SLOJudgeInfra(BaseModel):
    latency: Optional[SLOJudgeInfraLatency] = None
    availability: Optional[SLOJudgeInfraAvailability] = None
    sig: Optional[SLOJudgeInfraSignature] = None


class SLOCanaryThresholds(BaseModel):
    max_p95_rel_increase: float = 0.15
    max_error_abs_delta: float = 0.01
    max_sig_error_delta: float = 0.0005


class SLOCanary(BaseModel):
    thresholds: SLOCanaryThresholds = SLOCanaryThresholds()
    min_sample_count: int = 1000
    guardband_minutes: int = 10


class SLOQuorum(BaseModel):
    """합의 조건"""

    k: int = 2
    n: int = 3
    fail_closed_on_degrade: bool = True


class SLOSpec(BaseModel):
    """전체 SLO 정의"""

    version: str = "v1"
    budget: SLOBudget = SLOBudget()
    quota: SLOQuota = SLOQuota()
    anomaly: SLOAnomaly = SLOAnomaly()
    latency: SLOLatency = SLOLatency()
    error: SLOError = SLOError()
    witness: SLOWitness = SLOWitness()
    integrity: SLOIntegrity = SLOIntegrity()
    quorum: SLOQuorum = SLOQuorum()
    judge_infra: Optional[SLOJudgeInfra] = None
    canary: Optional[SLOCanary] = None
