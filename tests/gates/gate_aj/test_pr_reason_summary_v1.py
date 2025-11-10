import pytest

from scripts.ci.annotate_release_gate import _summarize

pytestmark = [pytest.mark.gate_aj]


def test_pr_summary_contains_codes_and_messages():
    decision = "fail"
    info = {"reasons": [{"code": "perf.p95_over", "message": "p95 지연 한계 초과"}]}
    trend = {
        "window_days": 7,
        "total_top": [["perf.p95_over", 3], ["quota.forbidden_action", 1]],
    }
    artifacts = [{"name": "reason-trend", "url": "https://example/artifacts"}]
    body = _summarize(decision, info, trend, "ko-KR", artifacts)
    assert "perf.p95_over" in body
    assert "p95 지연" in body
    assert "최근 추세" in body
    assert "Artifacts" in body
