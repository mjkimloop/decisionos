"""
Ops Cards 상한선 가시화 테스트 (v0.5.11r-9)

검증:
- SLO에서 상한선 추출
- Cards API 응답에 thresholds 포함
- 상한선 초과 감지
"""
import pytest
import json
from pathlib import Path
from apps.ops.cards.thresholds import (
    load_slo_thresholds,
    check_threshold_exceeded,
    format_threshold_status,
)

pytestmark = [pytest.mark.gate_ops]


@pytest.fixture
def slo_with_thresholds(tmp_path):
    """상한선이 있는 SLO 파일"""
    slo = {
        "version": "v2",
        "latency": {
            "max_p95_ms": 780,
            "baseline_p95_ms": 650,
            "max_p99_ms": 1440,
        },
        "budget": {
            "max_spent": 0.5,
        },
        "error": {
            "max_error_rate": 0.006,
        }
    }
    slo_file = tmp_path / "slo.json"
    slo_file.write_text(json.dumps(slo, indent=2), encoding="utf-8")
    return str(slo_file)


def test_load_slo_thresholds(slo_with_thresholds):
    """SLO에서 상한선 로드"""
    thresholds = load_slo_thresholds(slo_with_thresholds)

    assert thresholds["max_latency_ms"] == 780
    assert thresholds["baseline_latency_ms"] == 650
    assert thresholds["max_cost_usd"] == 0.5
    assert thresholds["max_error_rate"] == 0.006


def test_load_slo_missing_file(tmp_path):
    """SLO 파일 없을 때 빈 dict 반환"""
    thresholds = load_slo_thresholds(str(tmp_path / "nonexistent.json"))

    assert thresholds == {}


def test_check_threshold_exceeded():
    """상한선 초과 체크"""
    assert check_threshold_exceeded(800, 780) is True
    assert check_threshold_exceeded(750, 780) is False
    assert check_threshold_exceeded(780, 780) is False  # 동일값은 초과 아님


def test_format_threshold_status_normal():
    """정상 범위 내"""
    status = format_threshold_status(current=650, max_threshold=780, baseline=650)

    assert status["current"] == 650
    assert status["max"] == 780
    assert status["baseline"] == 650
    assert status["exceeded"] is False
    assert status["utilization_pct"] == pytest.approx(83.33, rel=0.1)


def test_format_threshold_status_exceeded():
    """상한선 초과"""
    status = format_threshold_status(current=800, max_threshold=780)

    assert status["current"] == 800
    assert status["max"] == 780
    assert status["exceeded"] is True
    assert status["utilization_pct"] == pytest.approx(102.56, rel=0.1)


def test_format_threshold_status_zero_max():
    """max=0 예외 처리"""
    status = format_threshold_status(current=100, max_threshold=0)

    assert status["utilization_pct"] == 0.0


def test_cards_api_includes_thresholds(tmp_path):
    """Cards API 응답에 thresholds 포함 확인"""
    from apps.ops.cards.thresholds import load_slo_thresholds

    # SLO 파일 생성
    slo = {
        "latency": {"max_p95_ms": 1000, "baseline_p95_ms": 800},
        "budget": {"max_spent": 1.0},
    }
    slo_file = tmp_path / "slo.json"
    slo_file.write_text(json.dumps(slo), encoding="utf-8")

    # 로드 테스트
    thresholds = load_slo_thresholds(str(slo_file))

    assert "max_latency_ms" in thresholds
    assert "max_cost_usd" in thresholds
    assert thresholds["max_latency_ms"] == 1000
    assert thresholds["max_cost_usd"] == 1.0


def test_threshold_utilization_calculations():
    """활용률 계산 정확도"""
    # 50% 활용
    status = format_threshold_status(390, 780)
    assert status["utilization_pct"] == 50.0

    # 100% 활용
    status = format_threshold_status(780, 780)
    assert status["utilization_pct"] == 100.0

    # 120% 초과
    status = format_threshold_status(936, 780)
    assert status["utilization_pct"] == 120.0


def test_partial_slo_thresholds(tmp_path):
    """일부 필드만 있는 SLO"""
    slo = {
        "latency": {"max_p95_ms": 500},  # baseline 없음
        # budget 없음
    }
    slo_file = tmp_path / "partial_slo.json"
    slo_file.write_text(json.dumps(slo), encoding="utf-8")

    thresholds = load_slo_thresholds(str(slo_file))

    assert "max_latency_ms" in thresholds
    assert "baseline_latency_ms" not in thresholds
    assert "max_cost_usd" not in thresholds


def test_invalid_json_slo(tmp_path):
    """잘못된 JSON SLO 파일"""
    slo_file = tmp_path / "invalid.json"
    slo_file.write_text("{ invalid json", encoding="utf-8")

    thresholds = load_slo_thresholds(str(slo_file))

    assert thresholds == {}


def test_threshold_boundary_values():
    """경계값 테스트"""
    # 정확히 상한선
    assert check_threshold_exceeded(780, 780) is False

    # 1ms 초과
    assert check_threshold_exceeded(781, 780) is True

    # 1ms 미만
    assert check_threshold_exceeded(779, 780) is False
