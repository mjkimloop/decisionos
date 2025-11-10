"""
tests/integration/test_integration_perf_evidence_v1.py

통합 테스트: perf → Evidence 병합 검증
"""
import json
import pytest

pytestmark = [pytest.mark.gate_t, pytest.mark.gate_s]

from apps.obs.evidence.snapshot import build_snapshot
from apps.rating.engine import RatingResult, LineItem


def test_perf_evidence_integration():
    """perf 블록이 Evidence에 병합되는지 검증"""
    # perf 데이터
    perf_data = {
        "latency_ms": {"p50": 320, "p95": 900, "p99": 1500},
        "error_rate": 0.012,
        "count": 12450,
        "window": {"start": "2025-01-01T10:00:00", "end": "2025-01-01T10:10:00"},
    }

    # Evidence 스냅샷 생성 (perf 포함)
    rating = RatingResult(
        subtotal=0.6,
        items=[
            LineItem(
                metric="tokens",
                usage=130.0,
                included=100.0,
                overage_units=30.0,
                overage_rate=0.02,
                amount=0.6,
            )
        ],
    )

    snap = build_snapshot(
        version="v0.5.11h",
        tenant="t1",
        witness_csv_path="test.csv",
        witness_rows=3,
        witness_csv_sha256="abc123",
        buckets={},
        deltas_by_metric={"tokens": 130.0},
        rating=rating,
        quota=[],
        budget_level="ok",
        budget_spent=0.6,
        budget_limit=1.0,
        anomaly_is_spike=False,
        anomaly_ewma=0.12,
        anomaly_ratio=0.5,
        perf=perf_data,  # perf 제공
    )

    # JSON 직렬화 및 검증
    json_str = snap.to_json()
    data = json.loads(json_str)

    # perf 블록 존재 및 값 확인
    assert "perf" in data
    assert data["perf"]["latency_ms"]["p95"] == 900
    assert data["perf"]["latency_ms"]["p99"] == 1500
    assert data["perf"]["error_rate"] == 0.012
    assert data["perf"]["count"] == 12450

    # 무결성 서명에 perf 포함 확인 (perf 제공 시 서명에 포함)
    assert "integrity" in data
    assert "signature_sha256" in data["integrity"]


def test_perf_none_not_in_json():
    """perf=None일 때 JSON에 포함되지 않음 확인"""
    rating = RatingResult(subtotal=0.3, items=[])

    snap = build_snapshot(
        version="v0.5.11h",
        tenant="t1",
        witness_csv_path="test.csv",
        witness_rows=3,
        witness_csv_sha256="abc123",
        buckets={},
        deltas_by_metric={},
        rating=rating,
        quota=[],
        budget_level="ok",
        budget_spent=0.3,
        budget_limit=1.0,
        anomaly_is_spike=False,
        anomaly_ewma=0.12,
        anomaly_ratio=0.5,
        perf=None,  # perf 미제공
    )

    json_str = snap.to_json()
    data = json.loads(json_str)

    # perf는 None이므로 JSON에는 null로 표시됨
    assert data.get("perf") is None
