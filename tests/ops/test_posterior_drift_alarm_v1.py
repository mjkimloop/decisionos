import pytest
import os
import json
import subprocess
import sys

pytestmark = [pytest.mark.gate_ops]


def test_beta_kl_basic():
    """Beta KL divergence 계산"""
    from apps.ops.monitor.drift import beta_kl
    # 동일 분포
    kl = beta_kl(2.0, 2.0, 2.0, 2.0)
    assert kl == pytest.approx(0.0, abs=0.1)
    # 상이한 분포
    kl2 = beta_kl(10.0, 2.0, 2.0, 10.0)
    assert kl2 > 0.1


def test_classify_drift_no_drift():
    """Drift 없음"""
    from apps.ops.monitor.drift import classify_drift
    res = classify_drift(2.0, 2.0, 2.5, 2.5, kl_warn=0.1, kl_crit=0.5, abs_warn=0.15, abs_crit=0.30)
    assert res["severity"] == "info"
    assert "no_drift" in res["reason_codes"]


def test_classify_drift_warn():
    """Drift 경고"""
    from apps.ops.monitor.drift import classify_drift
    # 절대 차이 경고 수준
    res = classify_drift(2.0, 2.0, 5.0, 2.0, abs_warn=0.15, abs_crit=0.30)
    # prior_mean=0.5, post_mean=5/(5+2)≈0.714 → diff≈0.214 > 0.15
    assert res["severity"] in ("warn", "critical")
    assert res["abs_diff"] > 0.15


def test_classify_drift_critical():
    """Drift 위험"""
    from apps.ops.monitor.drift import classify_drift
    # 극단적 차이
    res = classify_drift(2.0, 2.0, 10.0, 1.0, abs_crit=0.30)
    # prior_mean=0.5, post_mean≈0.909 → diff≈0.409 > 0.30
    assert res["severity"] == "critical"
    assert "abs_diff_critical" in res["reason_codes"]


def test_posterior_drift_job(tmp_path):
    """Drift 체크 작업 실행"""
    # Prior
    prior = {"alpha": 2.0, "beta": 2.0}
    prior_path = tmp_path / "prior.json"
    prior_path.write_text(json.dumps(prior), encoding="utf-8")

    # Posterior (약간 차이)
    posterior = {"posterior": {"alpha": 5.0, "beta": 2.0}}
    post_path = tmp_path / "posterior.json"
    post_path.write_text(json.dumps(posterior), encoding="utf-8")

    out_path = tmp_path / "drift.json"

    subprocess.check_call([
        sys.executable, "-m", "jobs.posterior_drift_check",
        "--prior", str(prior_path),
        "--posterior", str(post_path),
        "--out", str(out_path),
        "--abs-warn", "0.15",
        "--abs-crit", "0.30"
    ])

    drift = json.loads(out_path.read_text(encoding="utf-8"))
    assert "severity" in drift
    assert drift["severity"] in ("info", "warn", "critical")
    assert "reason_codes" in drift
    assert isinstance(drift["reason_codes"], list)
