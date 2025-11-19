# tests/judge/test_slo_schema_v2_compat_v1.py
"""
Test SLO schema Pydantic v2 compatibility (v0.5.11u-15c).

Ensures SLO models work with both Pydantic v1 and v2.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from apps.judge.slo_schema import (
    SLOBudget,
    SLOQuota,
    SLOAnomaly,
    SLOLatency,
    SLOError,
    SLOJudgeInfra,
    SLOJudgeInfraLatency,
    SLOCanary,
    SLOCanaryThresholds,
    SLOQuorum,
    SLODrift,
    SLOSaturation,
    SLOSpec,
)
from apps.common.pydantic_compat import PYDANTIC_V2, model_to_dict


def test_slo_budget_defaults():
    """Test SLOBudget default values."""
    budget = SLOBudget()

    assert budget.allow_levels == ["ok", "warn"]
    assert budget.max_spent is None


def test_slo_budget_custom():
    """Test SLOBudget with custom values."""
    budget = SLOBudget(allow_levels=["ok"], max_spent=100.0)

    assert budget.allow_levels == ["ok"]
    assert budget.max_spent == 100.0


def test_slo_latency_thresholds():
    """Test SLOLatency with p95/p99 thresholds."""
    latency = SLOLatency(max_p95_ms=200, max_p99_ms=500, min_samples=1000)

    assert latency.max_p95_ms == 200
    assert latency.max_p99_ms == 500
    assert latency.min_samples == 1000


def test_slo_error_threshold():
    """Test SLOError with error rate threshold."""
    error = SLOError(max_error_rate=0.01, min_samples=500)

    assert error.max_error_rate == 0.01
    assert error.min_samples == 500


def test_slo_judge_infra_nested():
    """Test SLOJudgeInfra with nested models."""
    infra = SLOJudgeInfra(
        latency=SLOJudgeInfraLatency(max_p95_ms=100, max_p99_ms=300),
        window_sec=600,
        grace_burst=0.1,
    )

    assert infra.latency.max_p95_ms == 100
    assert infra.latency.max_p99_ms == 300
    assert infra.window_sec == 600
    assert infra.grace_burst == 0.1


def test_slo_canary_defaults():
    """Test SLOCanary with default thresholds."""
    canary = SLOCanary()

    assert canary.thresholds.max_p95_rel_increase == 0.15
    assert canary.thresholds.max_error_abs_delta == 0.01
    assert canary.min_sample_count == 1000


def test_slo_quorum_defaults():
    """Test SLOQuorum k-of-n defaults."""
    quorum = SLOQuorum()

    assert quorum.k == 2
    assert quorum.n == 3
    assert quorum.fail_closed_on_degrade is True


def test_slo_drift_defaults():
    """Test SLODrift with defaults."""
    drift = SLODrift()

    assert drift.source == "var/alerts/posterior_drift.json"
    assert drift.max_abs_diff == 0.15
    assert drift.max_kl == 1.0
    assert drift.forbid_severity == ["critical"]


def test_slo_saturation_defaults():
    """Test SLOSaturation resource limits."""
    saturation = SLOSaturation()

    assert saturation.max_cpu_percent == 90.0
    assert saturation.max_mem_percent == 85.0
    assert saturation.max_qps is None
    assert saturation.fail_closed is True


def test_slo_spec_full():
    """Test SLOSpec with all fields."""
    spec = SLOSpec(
        version="v1",
        budget=SLOBudget(allow_levels=["ok"], max_spent=100.0),
        latency=SLOLatency(max_p95_ms=200),
        error=SLOError(max_error_rate=0.01),
        canary=SLOCanary(min_sample_count=500),
        saturation=SLOSaturation(max_cpu_percent=80.0),
    )

    assert spec.version == "v1"
    assert spec.budget.allow_levels == ["ok"]
    assert spec.latency.max_p95_ms == 200
    assert spec.error.max_error_rate == 0.01
    assert spec.canary.min_sample_count == 500
    assert spec.saturation.max_cpu_percent == 80.0


def test_slo_spec_model_validate():
    """Test SLOSpec.model_validate() for v1/v2 compatibility."""
    data = {
        "version": "v1",
        "budget": {"allow_levels": ["ok", "warn"]},
        "latency": {"max_p95_ms": 250},
    }

    if PYDANTIC_V2:
        spec = SLOSpec.model_validate(data)
    else:
        spec = SLOSpec.parse_obj(data)

    assert spec.version == "v1"
    assert spec.latency.max_p95_ms == 250


def test_slo_spec_to_dict():
    """Test SLOSpec serialization to dict."""
    spec = SLOSpec(
        latency=SLOLatency(max_p95_ms=200),
        error=SLOError(max_error_rate=0.01),
    )

    result = model_to_dict(spec, exclude_none=True)

    assert "version" in result
    assert "latency" in result
    assert "error" in result
    assert result["latency"]["max_p95_ms"] == 200
    assert result["error"]["max_error_rate"] == 0.01


def test_slo_spec_extra_fields_forbidden():
    """Test SLOSpec rejects extra fields (v2 extra='forbid')."""
    data = {
        "version": "v1",
        "budget": {"allow_levels": ["ok"]},
        "unknown_field": "should_fail",
    }

    if PYDANTIC_V2:
        with pytest.raises(ValidationError) as exc_info:
            SLOSpec.model_validate(data)

        # В v2 extra='forbid' должен вызывать ошибку
        assert "unknown_field" in str(exc_info.value).lower() or "extra" in str(exc_info.value).lower()
    else:
        # В v1 без явного extra='forbid' поле игнорируется
        # Но мы можем проверить, что модель создается
        spec = SLOSpec.parse_obj(data)
        assert spec.version == "v1"


def test_slo_quota_forbid_actions():
    """Test SLOQuota with forbid_actions."""
    quota = SLOQuota(
        forbid_actions={
            "approve_limit": ["high", "critical"],
            "reject_limit": ["low"],
        }
    )

    assert "approve_limit" in quota.forbid_actions
    assert quota.forbid_actions["approve_limit"] == ["high", "critical"]


def test_slo_anomaly_allow_spike():
    """Test SLOAnomaly spike control."""
    anomaly_strict = SLOAnomaly(allow_spike=False)
    anomaly_lenient = SLOAnomaly(allow_spike=True)

    assert anomaly_strict.allow_spike is False
    assert anomaly_lenient.allow_spike is True
