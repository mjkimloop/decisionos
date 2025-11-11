import pytest
import json
import tempfile
from pathlib import Path

@pytest.mark.gate_ops
def test_baseline_slo_generation():
    """베이스라인 SLO 생성 테스트"""
    # 샘플 Evidence 데이터
    evidence = {
        "perf": {
            "p50": 200,
            "p95": 500,
            "p99": 1000,
            "max": 2000,
            "count": 10000
        },
        "errors": {
            "count": 50
        }
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        # Evidence 파일 생성
        evidence_path = Path(tmpdir) / "evidence.json"
        with open(evidence_path, 'w') as f:
            json.dump(evidence, f)

        # SLO 출력 경로
        slo_path = Path(tmpdir) / "slo-v2.json"

        # baseline_slo.py 실행
        import subprocess
        result = subprocess.run([
            "python", "scripts/ops/baseline_slo.py",
            "--evidence", str(evidence_path),
            "--out", str(slo_path),
            "--margin", "1.2"
        ], capture_output=True, text=True)

        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # 생성된 SLO 검증
        with open(slo_path, 'r') as f:
            slo = json.load(f)

        assert slo["version"] == "v2"
        # P95: 500 * 1.2 = 600
        assert slo["latency"]["max_p95_ms"] == 600
        # P99: 1000 * 1.2 = 1200
        assert slo["latency"]["max_p99_ms"] == 1200
        # Error rate: 50/10000 = 0.005, * 1.2 = 0.006
        assert slo["error"]["max_error_rate"] == 0.006
        assert slo["witness"]["min_samples"] == 100  # 1% of 10000

@pytest.mark.gate_ops
def test_baseline_error_rate_calculation():
    """에러율 계산 테스트"""
    from scripts.ops.baseline_slo import calculate_error_rate

    # 50 / 10000 = 0.5%
    assert calculate_error_rate(10000, 50) == 0.005

    # 100 / 1000 = 10%
    assert calculate_error_rate(1000, 100) == 0.1

    # 0 요청 시 0%
    assert calculate_error_rate(0, 0) == 0.0

@pytest.mark.gate_ops
def test_baseline_aggregate_multi_evidence():
    """여러 Evidence 파일 병합 테스트"""
    from scripts.ops.baseline_slo import aggregate_multi_evidence

    with tempfile.TemporaryDirectory() as tmpdir:
        # 3개의 Evidence 파일 생성
        for i in range(3):
            evidence = {
                "perf": {
                    "p50": 200 + i * 10,
                    "p95": 500 + i * 50,
                    "p99": 1000 + i * 100,
                    "count": 1000
                },
                "errors": {
                    "count": 10
                }
            }
            with open(Path(tmpdir) / f"evidence_{i}.json", 'w') as f:
                json.dump(evidence, f)

        paths = [str(Path(tmpdir) / f"evidence_{i}.json") for i in range(3)]
        result = aggregate_multi_evidence(paths)

        # P95 평균: (500 + 550 + 600) / 3 = 550
        assert result["latency_p95"] == 550
        # P99 평균: (1000 + 1100 + 1200) / 3 = 1100
        assert result["latency_p99"] == 1100
        # 총 요청: 3000
        assert result["total_requests"] == 3000
        # 총 에러: 30
        assert result["error_count"] == 30

@pytest.mark.gate_ops
def test_baseline_safety_margin():
    """안전 마진 적용 테스트"""
    from scripts.ops.baseline_slo import generate_slo_v2

    baseline = {
        "latency_p95": 500,
        "latency_p99": 1000,
        "total_requests": 10000,
        "error_count": 100  # 1%
    }

    # 1.5배 마진 (50% 여유)
    slo = generate_slo_v2(baseline, safety_margin=1.5)

    assert slo["latency"]["max_p95_ms"] == 750  # 500 * 1.5
    assert slo["latency"]["max_p99_ms"] == 1500  # 1000 * 1.5
    assert slo["error"]["max_error_rate"] == 0.015  # 0.01 * 1.5

@pytest.mark.gate_ops
def test_baseline_min_samples():
    """최소 샘플 수 계산 테스트"""
    from scripts.ops.baseline_slo import generate_slo_v2

    # 1000 요청 → 최소 10 샘플 (1%)
    baseline = {
        "latency_p95": 500,
        "latency_p99": 1000,
        "total_requests": 1000,
        "error_count": 5
    }
    slo = generate_slo_v2(baseline)
    assert slo["witness"]["min_samples"] == 10

    # 100 요청 → 최소 10 샘플 (하한선)
    baseline["total_requests"] = 100
    slo = generate_slo_v2(baseline)
    assert slo["witness"]["min_samples"] == 10

    # 100000 요청 → 최소 1000 샘플
    baseline["total_requests"] = 100000
    slo = generate_slo_v2(baseline)
    assert slo["witness"]["min_samples"] == 1000
