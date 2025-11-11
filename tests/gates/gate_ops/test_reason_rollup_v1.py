import pytest
import json
from apps.ops.cards.aggregation import rollup_counts, palette_with_desc

@pytest.mark.gate_ops
def test_rollup_basic():
    # 가짜 카탈로그/그룹 주입은 생략(실제 파일 사용). 최소 기능 체크:
    reasons = ["reason:infra-latency","reason:infra-error","reason:perf","reason:canary"]
    r = rollup_counts(reasons)
    assert "groups" in r
    assert "Infra" in r["groups"]
    assert r["groups"]["Infra"] >= 2
    assert len(r["top"]) >= 1

@pytest.mark.gate_ops
def test_palette_present():
    pal = palette_with_desc()
    # 카탈로그에 정의된 reason:* 중 일부는 존재해야 함
    assert isinstance(pal, dict)
    # At least some labels should be present
    assert len(pal) > 0
