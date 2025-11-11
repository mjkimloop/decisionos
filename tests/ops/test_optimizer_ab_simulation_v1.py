import pytest
from apps.ops.optimizer.simulator import simulate_ab

pytestmark = [pytest.mark.gate_ops]


def test_simulate_ab_basic():
    """기본 A/B 시뮬레이션 동작 확인"""
    index = {"infra": {"incidents": 2, "cost": 1.0}, "perf": {"incidents": 1, "cost": 0.3}}
    base = {"infra": 1.0, "perf": 1.0}
    cand = {"infra": 1.2, "perf": 0.9}
    rep = simulate_ab(index, base, cand, traffic_split=0.3)
    assert "delta" in rep and "objective" in rep["delta"]
    assert isinstance(rep["delta"]["risk"], float)
    assert "baseline" in rep
    assert "candidate" in rep


def test_simulate_ab_traffic_split_impact():
    """트래픽 분할이 리스크에 미치는 영향"""
    index = {"infra": {"incidents": 2, "cost": 1.0}}
    base = {"infra": 1.0}
    cand = {"infra": 1.5}

    # 낮은 트래픽 → 높은 리스크
    rep_low = simulate_ab(index, base, cand, traffic_split=0.1)
    # 높은 트래픽 → 낮은 리스크
    rep_high = simulate_ab(index, base, cand, traffic_split=0.9)

    assert rep_low["delta"]["risk"] > rep_high["delta"]["risk"]


def test_simulate_ab_equal_weights():
    """동일 가중치일 때 delta = 0"""
    index = {"infra": {"incidents": 2, "cost": 1.0}, "perf": {"incidents": 1, "cost": 0.5}}
    base = {"infra": 1.0, "perf": 1.0}
    cand = {"infra": 1.0, "perf": 1.0}
    rep = simulate_ab(index, base, cand)
    assert rep["delta"]["objective"] == 0.0
    assert rep["baseline"]["objective"] == rep["candidate"]["objective"]


def test_sandbox_catalog_write(tmp_path):
    """샌드박스 카탈로그 생성"""
    import json
    from apps.ops.optimizer.sandbox import write_sandbox_catalog

    cat = {
        "groups": {
            "infra": {"weight": 1.3},
            "perf": {"weight": 1.1}
        }
    }
    cat_file = tmp_path / "catalog.json"
    cat_file.write_text(json.dumps(cat), encoding="utf-8")

    suggested = {"infra": 1.5, "perf": 0.9}
    out = write_sandbox_catalog(str(cat_file), suggested, str(tmp_path / "sandbox.json"))

    sandbox = json.load(open(out, "r", encoding="utf-8"))
    assert sandbox["groups"]["infra"]["weight"] == 1.5
    assert sandbox["groups"]["perf"]["weight"] == 0.9
