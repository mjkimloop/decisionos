"""
apps/judge/slo_schema.py

SLO-as-Code 모델 정의 (Pydantic v2 compatible)
"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from apps.common.pydantic_compat import PYDANTIC_V2

if PYDANTIC_V2:
    from pydantic import ConfigDict


class SLOBudget(BaseModel):
    """예산 제약 (allow_levels, max_spent)"""
    allow_levels: List[str] = Field(default_factory=lambda: ["ok", "warn"])
    max_spent: Optional[float] = None

    if PYDANTIC_V2:
        model_config = ConfigDict(extra='forbid')


class SLOQuota(BaseModel):
    """쿼터 제약 (forbid_actions)"""
    forbid_actions: Dict[str, List[str]] = Field(default_factory=dict)

    if PYDANTIC_V2:
        model_config = ConfigDict(extra='forbid')


class SLOAnomaly(BaseModel):
    """이상 징후 허용 (allow_spike)"""
    allow_spike: bool = False

    if PYDANTIC_V2:
        model_config = ConfigDict(extra='forbid')


class SLOWitness(BaseModel):
    """증거 검증 요구사항"""
    require_csv_sha256: bool = True
    require_signature: bool = True
    min_rows: int = 1

    if PYDANTIC_V2:
        model_config = ConfigDict(extra='forbid')


class SLOIntegrity(BaseModel):
    """무결성 검증 (signature)"""
    require_signature: bool = True

    if PYDANTIC_V2:
        model_config = ConfigDict(extra='forbid')


class SLOLatency(BaseModel):
    """레이턴시 임계값 (p95/p99)"""
    max_p95_ms: Optional[int] = None
    max_p99_ms: Optional[int] = None
    min_samples: Optional[int] = None

    if PYDANTIC_V2:
        model_config = ConfigDict(extra='forbid')


class SLOError(BaseModel):
    """에러율 임계값"""
    max_error_rate: Optional[float] = None
    min_samples: Optional[int] = None

    if PYDANTIC_V2:
        model_config = ConfigDict(extra='forbid')


class SLOJudgeInfraLatency(BaseModel):
    """Judge 인프라 레이턴시"""
    max_p95_ms: Optional[int] = None
    max_p99_ms: Optional[int] = None
    min_samples: Optional[int] = None

    if PYDANTIC_V2:
        model_config = ConfigDict(extra='forbid')


class SLOJudgeInfraAvailability(BaseModel):
    """Judge 인프라 가용성"""
    min_availability: Optional[float] = None

    if PYDANTIC_V2:
        model_config = ConfigDict(extra='forbid')


class SLOJudgeInfraSignature(BaseModel):
    """Judge 서명 에러율"""
    max_sig_error_rate: Optional[float] = None
    min_samples: Optional[int] = None

    if PYDANTIC_V2:
        model_config = ConfigDict(extra='forbid')


class SLOJudgeInfra(BaseModel):
    """Judge 인프라 SLO"""
    latency: Optional[SLOJudgeInfraLatency] = None
    availability: Optional[SLOJudgeInfraAvailability] = None
    sig: Optional[SLOJudgeInfraSignature] = None
    window_sec: int = 300
    grace_burst: float = 0.0

    if PYDANTIC_V2:
        model_config = ConfigDict(extra='forbid')


class SLOCanaryThresholds(BaseModel):
    """카나리 배포 임계값"""
    max_p95_rel_increase: float = 0.15
    max_error_abs_delta: float = 0.01
    max_sig_error_delta: float = 0.0005

    if PYDANTIC_V2:
        model_config = ConfigDict(extra='forbid')


class SLOCanary(BaseModel):
    """카나리 배포 SLO"""
    thresholds: SLOCanaryThresholds = SLOCanaryThresholds()
    min_sample_count: int = 1000
    guardband_minutes: int = 10

    if PYDANTIC_V2:
        model_config = ConfigDict(extra='forbid')


class SLOQuorum(BaseModel):
    """쿼럼 설정 (k-of-n)"""
    k: int = 2
    n: int = 3
    fail_closed_on_degrade: bool = True

    if PYDANTIC_V2:
        model_config = ConfigDict(extra='forbid')


class SLODrift(BaseModel):
    """모델 드리프트 검증"""
    source: str = Field(default="var/alerts/posterior_drift.json")
    max_abs_diff: float = 0.15
    max_kl: float = 1.0
    forbid_severity: List[str] = Field(default_factory=lambda: ["critical"])

    if PYDANTIC_V2:
        model_config = ConfigDict(extra='forbid')


class SLOSaturation(BaseModel):
    """리소스 포화도 제한 (cpu/mem/qps)"""
    max_cpu_percent: Optional[float] = 90.0
    max_mem_percent: Optional[float] = 85.0
    max_qps: Optional[int] = None
    fail_closed: bool = True

    if PYDANTIC_V2:
        model_config = ConfigDict(extra='forbid')


class SLOSpec(BaseModel):
    """SLO 전체 스펙 (v1)"""
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
    drift: Optional[SLODrift] = None
    saturation: Optional[SLOSaturation] = None

    if PYDANTIC_V2:
        model_config = ConfigDict(extra='forbid')
