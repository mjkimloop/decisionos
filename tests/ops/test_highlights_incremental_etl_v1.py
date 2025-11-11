import pytest
import os
import json
import subprocess
import sys

pytestmark = [pytest.mark.gate_ops]


def test_incr_etl_basic(tmp_path):
    """기본 증분 ETL 동작"""
    idx1 = {"rev": "r1", "rows": [{"group": "infra", "label": "reason:infra-latency", "count": 5}]}
    (tmp_path / "summary.json").write_text(json.dumps(idx1), encoding="utf-8")
    cat = {
        "groups": {"infra": {"weight": 1.0}},
        "labels": [{"name": "reason:infra-latency"}]
    }
    (tmp_path / "catalog.json").write_text(json.dumps(cat), encoding="utf-8")
    outdir = tmp_path / "hl"

    # 1차 실행
    subprocess.check_call([
        sys.executable, "jobs/etl_highlights_incremental.py",
        "--index", str(tmp_path / "summary.json"),
        "--catalog", str(tmp_path / "catalog.json"),
        "--out-dir", str(outdir),
        "--k", "5"
    ])

    latest1 = json.loads((outdir / "latest.json").read_text(encoding="utf-8"))
    assert latest1["rev"] == "r1"
    token1 = latest1["token"]

    # 2차 실행 (리비전 변경)
    idx2 = {"rev": "r2", "rows": [{"group": "infra", "label": "reason:infra-latency", "count": 8}]}
    (tmp_path / "summary.json").write_text(json.dumps(idx2), encoding="utf-8")

    subprocess.check_call([
        sys.executable, "jobs/etl_highlights_incremental.py",
        "--index", str(tmp_path / "summary.json"),
        "--catalog", str(tmp_path / "catalog.json"),
        "--out-dir", str(outdir),
        "--k", "5"
    ])

    latest2 = json.loads((outdir / "latest.json").read_text(encoding="utf-8"))
    assert latest2["rev"] == "r2"
    assert latest2["token"] != token1

    # 스트림 존재
    assert (outdir / "stream.jsonl").exists()


def test_incr_etl_same_revision(tmp_path):
    """동일 리비전 재실행 시 증분 없음"""
    idx = {"rev": "r1", "rows": [{"group": "infra", "label": "reason:infra-latency", "count": 5}]}
    (tmp_path / "summary.json").write_text(json.dumps(idx), encoding="utf-8")
    cat = {
        "groups": {"infra": {"weight": 1.0}},
        "labels": [{"name": "reason:infra-latency"}]
    }
    (tmp_path / "catalog.json").write_text(json.dumps(cat), encoding="utf-8")
    outdir = tmp_path / "hl"

    # 1차
    subprocess.check_call([
        sys.executable, "jobs/etl_highlights_incremental.py",
        "--index", str(tmp_path / "summary.json"),
        "--catalog", str(tmp_path / "catalog.json"),
        "--out-dir", str(outdir),
        "--k", "5"
    ])

    stream1_lines = (outdir / "stream.jsonl").read_text(encoding="utf-8").count("\n")

    # 2차 (동일 리비전)
    subprocess.check_call([
        sys.executable, "jobs/etl_highlights_incremental.py",
        "--index", str(tmp_path / "summary.json"),
        "--catalog", str(tmp_path / "catalog.json"),
        "--out-dir", str(outdir),
        "--k", "5"
    ])

    stream2_lines = (outdir / "stream.jsonl").read_text(encoding="utf-8").count("\n")
    # 동일 리비전이면 스트림 append 안 함
    assert stream1_lines == stream2_lines


def test_highlights_ranking(tmp_path):
    """하이라이트 순위 매기기"""
    idx = {
        "rev": "r1",
        "rows": [
            {"group": "infra", "label": "reason:infra-latency", "count": 10},
            {"group": "perf", "label": "reason:perf", "count": 5},
            {"group": "canary", "label": "reason:canary", "count": 2}
        ]
    }
    (tmp_path / "summary.json").write_text(json.dumps(idx), encoding="utf-8")
    cat = {
        "groups": {
            "infra": {"weight": 1.0},
            "perf": {"weight": 1.5},
            "canary": {"weight": 1.0}
        },
        "labels": [
            {"name": "reason:infra-latency"},
            {"name": "reason:perf"},
            {"name": "reason:canary"}
        ]
    }
    (tmp_path / "catalog.json").write_text(json.dumps(cat), encoding="utf-8")
    outdir = tmp_path / "hl"

    subprocess.check_call([
        sys.executable, "jobs/etl_highlights_incremental.py",
        "--index", str(tmp_path / "summary.json"),
        "--catalog", str(tmp_path / "catalog.json"),
        "--out-dir", str(outdir),
        "--k", "3",
        "--weighted"
    ])

    latest = json.loads((outdir / "latest.json").read_text(encoding="utf-8"))
    items = latest["items"]
    assert len(items) == 3
    # 가중치 적용: infra=10*1.0=10, perf=5*1.5=7.5, canary=2*1.0=2
    # infra가 1위
    assert items[0]["rank"] == 1
    assert items[0]["label"] == "reason:infra-latency"
    assert items[0]["value"] == 10.0
    # perf가 2위
    assert items[1]["rank"] == 2
    assert items[1]["label"] == "reason:perf"
    assert items[1]["value"] == 7.5
