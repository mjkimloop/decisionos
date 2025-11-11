"""
DR/카오스 시나리오: 쿼럼 퇴화 검증 (v0.5.11r-7)

시나리오:
- SLO 쿼럼: K=2/N=3 (3대 중 2대 동의 필요)
- 1대 다운 → 쿼럼 유지 (2대 가용)
- 2대 다운 → 쿼럼 미달 → fail-closed

검증:
- fail_closed_on_degrade=true 시 배포 차단
- stage=abort, exit 2
"""
import pytest
import json
from pathlib import Path

pytestmark = [pytest.mark.chaos]


@pytest.fixture
def slo_quorum_config(tmp_path):
    """쿼럼 설정이 있는 SLO"""
    slo = {
        "version": "v2",
        "quorum": {
            "k": 2,
            "n": 3,
            "fail_closed_on_degrade": True
        },
        "witness": {
            "require_signature": True,
            "min_rows": 1
        },
        "integrity": {
            "require_signature": True
        }
    }
    slo_file = tmp_path / "slo.json"
    slo_file.write_text(json.dumps(slo, indent=2), encoding="utf-8")
    return slo_file


@pytest.fixture
def mock_judge_cluster():
    """3대 Judge 클러스터 시뮬레이션"""
    return {
        "judge-1": {"status": "healthy", "ready": True},
        "judge-2": {"status": "healthy", "ready": True},
        "judge-3": {"status": "healthy", "ready": True},
    }


def check_quorum_met(cluster: dict, k: int, n: int) -> bool:
    """쿼럼 충족 여부 확인"""
    ready_count = sum(1 for j in cluster.values() if j["ready"])
    return ready_count >= k


def decide_deployment(cluster: dict, k: int, n: int, fail_closed: bool) -> str:
    """배포 결정 (쿼럼 기반)"""
    quorum_met = check_quorum_met(cluster, k, n)

    if not quorum_met:
        if fail_closed:
            return "abort"
        else:
            return "proceed_with_warning"

    return "proceed"


def test_chaos_quorum_all_healthy(mock_judge_cluster):
    """정상: 3대 모두 가용 → proceed"""
    decision = decide_deployment(mock_judge_cluster, k=2, n=3, fail_closed=True)
    assert decision == "proceed"


def test_chaos_quorum_one_down_ok(mock_judge_cluster):
    """1대 다운: 2/3 가용 → K=2 충족 → proceed"""
    mock_judge_cluster["judge-3"]["ready"] = False

    decision = decide_deployment(mock_judge_cluster, k=2, n=3, fail_closed=True)
    assert decision == "proceed"


def test_chaos_quorum_two_down_fail_closed(mock_judge_cluster):
    """2대 다운: 1/3 가용 → K=2 미달 → fail-closed → abort"""
    mock_judge_cluster["judge-2"]["ready"] = False
    mock_judge_cluster["judge-3"]["ready"] = False

    decision = decide_deployment(mock_judge_cluster, k=2, n=3, fail_closed=True)
    assert decision == "abort"


def test_chaos_quorum_two_down_no_fail_closed(mock_judge_cluster):
    """2대 다운 + fail_closed=False → proceed_with_warning"""
    mock_judge_cluster["judge-2"]["ready"] = False
    mock_judge_cluster["judge-3"]["ready"] = False

    decision = decide_deployment(mock_judge_cluster, k=2, n=3, fail_closed=False)
    assert decision == "proceed_with_warning"


def test_chaos_quorum_all_down_abort(mock_judge_cluster):
    """전체 다운: 0/3 가용 → 무조건 abort"""
    for judge in mock_judge_cluster.values():
        judge["ready"] = False

    decision = decide_deployment(mock_judge_cluster, k=2, n=3, fail_closed=True)
    assert decision == "abort"


def test_chaos_quorum_config_validation(slo_quorum_config):
    """SLO 쿼럼 설정 검증"""
    slo = json.loads(slo_quorum_config.read_text(encoding="utf-8"))

    quorum = slo["quorum"]
    assert quorum["k"] == 2
    assert quorum["n"] == 3
    assert quorum["fail_closed_on_degrade"] is True


def test_chaos_quorum_k_equal_n_strict():
    """K=N (엄격 모드): 1대라도 다운 시 abort"""
    cluster = {
        "judge-1": {"ready": True},
        "judge-2": {"ready": True},
        "judge-3": {"ready": False},  # 1대 다운
    }

    decision = decide_deployment(cluster, k=3, n=3, fail_closed=True)
    assert decision == "abort"


def test_chaos_quorum_k_1_n_3_relaxed():
    """K=1/N=3 (완화 모드): 1대만 가용해도 proceed"""
    cluster = {
        "judge-1": {"ready": True},
        "judge-2": {"ready": False},
        "judge-3": {"ready": False},
    }

    decision = decide_deployment(cluster, k=1, n=3, fail_closed=True)
    assert decision == "proceed"


def test_chaos_quorum_exit_code_simulation():
    """배포 스크립트 exit code 시뮬레이션"""
    cluster_degraded = {
        "judge-1": {"ready": True},
        "judge-2": {"ready": False},
        "judge-3": {"ready": False},
    }

    decision = decide_deployment(cluster_degraded, k=2, n=3, fail_closed=True)

    # 실제 배포 스크립트 exit code 매핑
    exit_code = {
        "proceed": 0,
        "abort": 2,
        "proceed_with_warning": 1,
    }[decision]

    assert exit_code == 2  # abort → exit 2


def test_chaos_quorum_gradual_degradation():
    """점진적 퇴화 시나리오"""
    cluster = {
        "judge-1": {"ready": True},
        "judge-2": {"ready": True},
        "judge-3": {"ready": True},
    }

    # T0: 모두 정상
    assert decide_deployment(cluster, k=2, n=3, fail_closed=True) == "proceed"

    # T1: 1대 다운 (쿼럼 유지)
    cluster["judge-3"]["ready"] = False
    assert decide_deployment(cluster, k=2, n=3, fail_closed=True) == "proceed"

    # T2: 2대 다운 (쿼럼 미달)
    cluster["judge-2"]["ready"] = False
    assert decide_deployment(cluster, k=2, n=3, fail_closed=True) == "abort"

    # T3: 복구 (쿼럼 회복)
    cluster["judge-2"]["ready"] = True
    assert decide_deployment(cluster, k=2, n=3, fail_closed=True) == "proceed"
