import pytest
from apps.ops.optimizer.bayes import WeightOptimizer, SearchSpace, default_loglik_from_index, HistoryPoint

pytestmark = [pytest.mark.gate_ops]

def test_optimizer_suggest_basic():
    """기본 베이지안 탐색 동작 확인"""
    space = SearchSpace(bounds={"infra": (0.5, 1.5), "perf": (0.5, 1.5)})
    index = {"infra": {"incidents": 2, "cost": 1.0}, "perf": {"incidents": 1, "cost": 0.5}}
    loglik = default_loglik_from_index(index)
    hist = [HistoryPoint(weights={"infra": 1.0, "perf": 1.0}, objective=loglik({"infra": 1.0, "perf": 1.0}), meta={})]
    w = WeightOptimizer(space).suggest(hist, loglik, n_iter=20)
    assert 0.5 <= w["infra"] <= 1.5 and 0.5 <= w["perf"] <= 1.5


def test_optimizer_with_empty_history():
    """히스토리 없이도 동작 확인"""
    space = SearchSpace(bounds={"quota": (0.5, 1.2)})
    index = {"quota": {"incidents": 0, "cost": 0.2}}
    loglik = default_loglik_from_index(index)
    w = WeightOptimizer(space).suggest([], loglik, n_iter=10)
    assert "quota" in w
    assert 0.5 <= w["quota"] <= 1.2


def test_loglik_function():
    """목적함수 계산 확인"""
    index = {"infra": {"incidents": 5, "cost": 2.0}, "perf": {"incidents": 1, "cost": 0.3}}
    loglik = default_loglik_from_index(index)
    score1 = loglik({"infra": 1.0, "perf": 1.0})
    score2 = loglik({"infra": 1.5, "perf": 0.8})
    # 점수는 incidents 적을수록 높음
    assert isinstance(score1, float)
    assert isinstance(score2, float)


def test_build_space_from_catalog(tmp_path):
    """카탈로그로부터 탐색 공간 생성"""
    import json
    from apps.ops.optimizer.bayes import build_space_from_catalog
    cat = {
        "groups": {
            "infra": {"weight": 1.3},
            "perf": {"weight": 1.1}
        }
    }
    cat_file = tmp_path / "catalog.json"
    cat_file.write_text(json.dumps(cat), encoding="utf-8")
    space = build_space_from_catalog(str(cat_file))
    assert "infra" in space.bounds
    assert "perf" in space.bounds
    # 기본 범위: ±50%
    assert space.bounds["infra"][0] == 1.3 * 0.5
    assert space.bounds["infra"][1] == 1.3 * 1.5
