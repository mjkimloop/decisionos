"""
apps/judge/slo_schema.py

SLO-as-Code 모델 정의 (Pydantic)
"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SLOBudget(BaseModel):
    allow_levels: List[str] = Field(default_factory=lambda: ["ok", "warn"])
    max_spent: Optional[float] = None


class SLOQuota(BaseModel):
    forbid_actions: Dict[str, List[str]] = Field(default_factory=dict)


class SLOAnomaly(BaseModel):
    allow_spike: bool = False


class SLOWitness(BaseModel):
    require_csv_sha256: bool = True
    require_signature: bool = True
    min_rows: int = 1


class SLOIntegrity(BaseModel):
    require_signature: bool = True


class SLOLatency(BaseModel):
    max_p95_ms: Optional[int] = None
    max_p99_ms: Optional[int] = None
    min_samples: Optional[int] = None


class SLOError(BaseModel):
    max_error_rate: Optional[float] = None
    min_samples: Optional[int] = None


class SLOJudgeInfraLatency(BaseModel):
    max_p95_ms: Optional[int] = None
    max_p99_ms: Optional[int] = None
    min_samples: Optional[int] = None


class SLOJudgeInfraAvailability(BaseModel):
    min_availability: Optional[float] = None


class SLOJudgeInfraSignature(BaseModel):
    max_sig_error_rate: Optional[float] = None
    min_samples: Optional[int] = None


class SLOJudgeInfra(BaseModel):
    latency: Optional[SLOJudgeInfraLatency] = None
    availability: Optional[SLOJudgeInfraAvailability] = None
    sig: Optional[SLOJudgeInfraSignature] = None
    window_sec: int = 300
    grace_burst: float = 0.0


class SLOCanaryThresholds(BaseModel):
    max_p95_rel_increase: float = 0.15
    max_error_abs_delta: float = 0.01
    max_sig_error_delta: float = 0.0005


class SLOCanary(BaseModel):
    thresholds: SLOCanaryThresholds = SLOCanaryThresholds()
    min_sample_count: int = 1000
    guardband_minutes: int = 10


class SLOQuorum(BaseModel):
    k: int = 2
    n: int = 3
    fail_closed_on_degrade: bool = True


class SLODrift(BaseModel):
    source: str = Field(default="var/alerts/posterior_drift.json")
    max_abs_diff: float = 0.15
    max_kl: float = 1.0
    forbid_severity: List[str] = Field(default_factory=lambda: ["critical"])


class SLOSpec(BaseModel):
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
