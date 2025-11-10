"""
tests/gates/gate_t/test_witness_perf_summary_v1.py

Gate-T: 성능 증빙 요약 테스트 (p50/p95/p99, error_rate)
"""
import io
import datetime as dt
import pytest

pytestmark = [pytest.mark.gate_t]

from apps.obs.witness.perf import parse_reqlog_csv, summarize_perf, Req


def test_parse_reqlog_csv():
    """CSV 파싱 테스트"""
    csv_data = """\
ts,status,latency_ms
2025-01-01T10:00:00,200,100.5
2025-01-01T10:00:01,200,150.2
2025-01-01T10:00:02,500,350.0
2025-01-01T10:00:03,429,200.0
"""
    reqs = parse_reqlog_csv(io.StringIO(csv_data))
    assert len(reqs) == 4
    assert reqs[0].status == 200
    assert reqs[0].latency_ms == 100.5
    assert reqs[2].status == 500
    assert reqs[3].status == 429


def test_summarize_perf_basic():
    """기본 성능 요약 테스트"""
    reqs = [
        Req(dt.datetime(2025, 1, 1, 10, 0, 0), 200, 100),
        Req(dt.datetime(2025, 1, 1, 10, 0, 1), 200, 200),
        Req(dt.datetime(2025, 1, 1, 10, 0, 2), 200, 300),
        Req(dt.datetime(2025, 1, 1, 10, 0, 3), 200, 400),
        Req(dt.datetime(2025, 1, 1, 10, 0, 4), 500, 500),  # error
        Req(dt.datetime(2025, 1, 1, 10, 0, 5), 200, 600),
        Req(dt.datetime(2025, 1, 1, 10, 0, 6), 200, 700),
        Req(dt.datetime(2025, 1, 1, 10, 0, 7), 200, 800),
        Req(dt.datetime(2025, 1, 1, 10, 0, 8), 200, 900),
        Req(dt.datetime(2025, 1, 1, 10, 0, 9), 200, 1000),
    ]
    summary = summarize_perf(reqs)

    assert summary["count"] == 10
    assert summary["latency_ms"]["p50"] == 600.0  # 50th percentile (idx=5)
    assert summary["latency_ms"]["p95"] == 1000.0  # 95th percentile (idx=9)
    assert summary["latency_ms"]["p99"] == 1000.0  # 99th percentile (idx=9)
    assert summary["error_rate"] == 0.1  # 1 error out of 10
    assert "window" in summary
    assert summary["window"]["start"] == "2025-01-01T10:00:00"
    assert summary["window"]["end"] == "2025-01-01T10:00:09"


def test_summarize_perf_with_429():
    """429 에러도 에러로 계산"""
    reqs = [
        Req(dt.datetime(2025, 1, 1, 10, 0, 0), 200, 100),
        Req(dt.datetime(2025, 1, 1, 10, 0, 1), 429, 200),  # rate limit error
        Req(dt.datetime(2025, 1, 1, 10, 0, 2), 500, 300),  # server error
        Req(dt.datetime(2025, 1, 1, 10, 0, 3), 200, 400),
    ]
    summary = summarize_perf(reqs)

    assert summary["count"] == 4
    assert summary["error_rate"] == 0.5  # 2 errors out of 4


def test_summarize_perf_empty():
    """빈 입력 처리"""
    summary = summarize_perf([])
    assert summary["count"] == 0
    assert "latency_ms" not in summary


def test_summarize_perf_1000_samples():
    """1000개 샘플로 p95/p99 검증"""
    # 균일 분포: 0~999ms
    reqs = [
        Req(dt.datetime(2025, 1, 1, 10, 0, i % 60), 200, float(i))
        for i in range(1000)
    ]
    # 에러 추가 (10개 = 1%)
    for i in range(10):
        reqs[i * 100] = Req(
            dt.datetime(2025, 1, 1, 10, 0, 0), 500, float(i * 100)
        )

    summary = summarize_perf(reqs)

    assert summary["count"] == 1000
    # p95 ~ 950ms (nearest-rank)
    assert 940 <= summary["latency_ms"]["p95"] <= 960
    # p99 ~ 990ms
    assert 980 <= summary["latency_ms"]["p99"] <= 1000
    # error_rate = 10/1000 = 0.01
    assert abs(summary["error_rate"] - 0.01) < 0.001
