import pytest
import json
import os
import subprocess
import sys
import pathlib

pytestmark = [pytest.mark.gate_ops]


def test_reconcile_basic(tmp_path):
    """기본 정합성 리포트 생성"""
    ab = {"delta": {"mean": 0.8}}
    can = {"delta": {"score_delta": 0.6}}
    (tmp_path / "ab_report.json").write_text(json.dumps(ab), encoding="utf-8")
    (tmp_path / "canary.json").write_text(json.dumps(can), encoding="utf-8")
    out = tmp_path / "rec.json"

    cmd = [
        sys.executable, "jobs/reconcile_canary_vs_offline.py",
        "--ab-report", str(tmp_path / "ab_report.json"),
        "--canary", str(tmp_path / "canary.json"),
        "--out", str(out)
    ]
    subprocess.check_call(cmd)

    rep = json.loads(out.read_text(encoding="utf-8"))
    assert "mae" in rep
    assert "sign_agreement" in rep
    assert "calibration_ratio" in rep
    assert "predicted_delta" in rep
    assert "observed_delta" in rep


def test_reconcile_sign_agreement(tmp_path):
    """부호 일치 확인"""
    # 동일 부호
    ab = {"delta": {"mean": 0.5}}
    can = {"delta": {"score_delta": 0.3}}
    (tmp_path / "ab.json").write_text(json.dumps(ab), encoding="utf-8")
    (tmp_path / "can.json").write_text(json.dumps(can), encoding="utf-8")
    out = tmp_path / "rec.json"

    subprocess.check_call([
        sys.executable, "jobs/reconcile_canary_vs_offline.py",
        "--ab-report", str(tmp_path / "ab.json"),
        "--canary", str(tmp_path / "can.json"),
        "--out", str(out)
    ])

    rep = json.loads(out.read_text(encoding="utf-8"))
    assert rep["sign_agreement"] is True


def test_reconcile_sign_disagreement(tmp_path):
    """부호 불일치 확인"""
    # 반대 부호
    ab = {"delta": {"mean": 0.5}}
    can = {"delta": {"score_delta": -0.3}}
    (tmp_path / "ab.json").write_text(json.dumps(ab), encoding="utf-8")
    (tmp_path / "can.json").write_text(json.dumps(can), encoding="utf-8")
    out = tmp_path / "rec.json"

    subprocess.check_call([
        sys.executable, "jobs/reconcile_canary_vs_offline.py",
        "--ab-report", str(tmp_path / "ab.json"),
        "--canary", str(tmp_path / "can.json"),
        "--out", str(out)
    ])

    rep = json.loads(out.read_text(encoding="utf-8"))
    assert rep["sign_agreement"] is False


def test_reconcile_fallback_to_objective(tmp_path):
    """mean 없을 때 objective로 fallback"""
    ab = {"delta": {"objective": 1.2}}  # mean 없음
    can = {"delta": {"score_delta": 1.0}}
    (tmp_path / "ab.json").write_text(json.dumps(ab), encoding="utf-8")
    (tmp_path / "can.json").write_text(json.dumps(can), encoding="utf-8")
    out = tmp_path / "rec.json"

    subprocess.check_call([
        sys.executable, "jobs/reconcile_canary_vs_offline.py",
        "--ab-report", str(tmp_path / "ab.json"),
        "--canary", str(tmp_path / "can.json"),
        "--out", str(out)
    ])

    rep = json.loads(out.read_text(encoding="utf-8"))
    assert rep["predicted_delta"] == 1.2
    assert rep["mae"] > 0
