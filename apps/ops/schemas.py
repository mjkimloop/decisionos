# apps/ops/schemas.py
"""
Ops API response schemas with Pydantic v2 support (v0.5.11u-15b).

Response models for Cards API, Heatmap, Circuit Breaker status.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from apps.common.pydantic_compat import PYDANTIC_V2

if PYDANTIC_V2:
    from pydantic import ConfigDict


# ===== Cards API Schemas =====

class ReasonTrendItem(BaseModel):
    """Individual reason with score and count."""
    reason: str = Field(..., description="Reason label")
    score: float = Field(..., description="Weighted score")
    count: int = Field(default=0, description="Event count")

    if PYDANTIC_V2:
        model_config = ConfigDict(
            from_attributes=True,
            populate_by_name=True,
        )
    else:
        class Config:
            orm_mode = True
            allow_population_by_field_name = True


class BucketGroupData(BaseModel):
    """Group aggregation within a bucket."""
    score: float = Field(default=0.0)
    count: int = Field(default=0)

    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class BucketEntry(BaseModel):
    """Time bucket with group aggregations."""
    ts: str = Field(..., description="ISO timestamp")
    bucket: str = Field(..., description="Bucket label (e.g., d-0, h-2)")
    groups: Dict[str, BucketGroupData] = Field(default_factory=dict)

    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class GroupSummary(BaseModel):
    """Group-level summary."""
    score: float = Field(default=0.0)
    count: int = Field(default=0)
    weight: float = Field(default=1.0)

    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class CardsSummary(BaseModel):
    """Overall summary statistics."""
    total_events: int = Field(default=0)
    unique_reasons: int = Field(default=0)

    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class CardsMeta(BaseModel):
    """Metadata about data sources."""
    index_path: Optional[str] = None
    weights_path: Optional[str] = None
    tenant: Optional[str] = None
    catalog_sha: Optional[str] = None

    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class CardsReasonTrendsResponse(BaseModel):
    """Response for /ops/cards/reason-trends endpoint."""
    generated_at: Optional[str] = Field(None, description="Index generation timestamp")
    period: str = Field(..., description="Query period (e.g., 7d, 24h)")
    bucket: str = Field(..., description="Bucket type (day, hour)")
    groups: Dict[str, GroupSummary] = Field(default_factory=dict)
    buckets: List[BucketEntry] = Field(default_factory=list)
    top_reasons: List[ReasonTrendItem] = Field(default_factory=list)
    summary: CardsSummary = Field(default_factory=CardsSummary)
    _meta: CardsMeta = Field(default_factory=CardsMeta, alias="_meta")

    if PYDANTIC_V2:
        model_config = ConfigDict(
            from_attributes=True,
            populate_by_name=True,
        )
    else:
        class Config:
            orm_mode = True
            allow_population_by_field_name = True


class CardsDeltaResponse(BaseModel):
    """Response for Cards Delta protocol (v0.5.11t)."""
    data: CardsReasonTrendsResponse
    delta: Optional[Dict[str, Any]] = Field(
        None,
        description="Delta changes (added, removed, changed)"
    )
    _meta: CardsMeta = Field(default_factory=CardsMeta, alias="_meta")

    if PYDANTIC_V2:
        model_config = ConfigDict(
            from_attributes=True,
            populate_by_name=True,
        )
    else:
        class Config:
            orm_mode = True
            allow_population_by_field_name = True


# ===== Circuit Breaker / Health Schemas =====

class CircuitBreakerState(BaseModel):
    """Circuit breaker state."""
    service: str
    state: str = Field(..., description="open, half_open, closed")
    failure_count: int = Field(default=0)
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None

    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class HealthCheckResponse(BaseModel):
    """Health check response."""
    ok: bool = Field(..., description="Overall health status")
    timestamp: float = Field(..., description="Check timestamp")
    services: Dict[str, Any] = Field(default_factory=dict)

    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


__all__ = [
    'ReasonTrendItem',
    'BucketEntry',
    'GroupSummary',
    'CardsSummary',
    'CardsMeta',
    'CardsReasonTrendsResponse',
    'CardsDeltaResponse',
    'CircuitBreakerState',
    'HealthCheckResponse',
]
