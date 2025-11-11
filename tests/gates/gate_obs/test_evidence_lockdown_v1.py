"""
Evidence 불변성 강화 테스트 (v0.5.11r-6)

무결성 검증:
- 인덱스 생성 및 SHA256 검증
- 변조 감지
- manifest.jsonl 생성
- S3 ObjectLock 시뮬레이션
"""
import json
import pytest
from pathlib import Path
from apps.obs.evidence.indexer import scan_dir, write_index

pytestmark = [pytest.mark.gate_obs]


@pytest.fixture
def evidence_dir(tmp_path):
    """테스트용 Evidence 디렉토리"""
    ev_dir = tmp_path / "evidence"
    ev_dir.mkdir()
    return ev_dir


@pytest.fixture
def sample_evidence(evidence_dir):
    """샘플 Evidence 파일 생성"""
    import hashlib
    from datetime import datetime, timezone

    # 정상 Evidence
    data = {
        "meta": {"tenant": "test", "generated_at": datetime.now(timezone.utc).isoformat()},
        "witness": {"csv_sha256": "abc123", "signature": "sig"},
        "usage": {"tokens_total": 1000},
        "rating": {"pass": True},
        "quota": {"level": "ok"},
        "budget": {"spent": 0.5},
        "anomaly": {"spike": False},
        "integrity": {}
    }

    # 코어 시그니처 계산
    core = {k: data[k] for k in ["meta", "witness", "usage", "rating", "quota", "budget", "anomaly"]}
    payload = json.dumps(core, ensure_ascii=False, sort_keys=True).encode("utf-8")
    data["integrity"]["signature_sha256"] = hashlib.sha256(payload).hexdigest()

    ev_file = evidence_dir / "evidence-001.json"
    ev_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return ev_file


def test_evidence_scan_basic(evidence_dir, sample_evidence):
    """기본 스캔 동작 테스트"""
    index = scan_dir(str(evidence_dir))

    assert index["summary"]["count"] == 1
    assert index["summary"]["tampered"] == 0
    assert index["summary"]["wip"] == 1  # .locked.json이 아니면 WIP
    assert index["summary"]["locked"] == 0

    files = index["files"]
    assert len(files) == 1
    assert files[0]["path"] == "evidence-001.json"
    assert files[0]["sha256"]  # SHA256 해시 존재
    assert not files[0]["tampered"]


def test_evidence_scan_tampered(evidence_dir, sample_evidence):
    """변조 감지 테스트"""
    # Evidence 파일 변조 (시그니처 변경)
    data = json.loads(sample_evidence.read_text(encoding="utf-8"))
    data["integrity"]["signature_sha256"] = "invalid_signature"
    sample_evidence.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    index = scan_dir(str(evidence_dir))

    assert index["summary"]["tampered"] == 1
    files = index["files"]
    assert files[0]["tampered"] is True


def test_evidence_locked_tier(evidence_dir):
    """LOCKED tier 감지 테스트"""
    import hashlib
    from datetime import datetime, timezone

    data = {
        "meta": {"tenant": "test", "generated_at": datetime.now(timezone.utc).isoformat()},
        "witness": {"csv_sha256": "abc"},
        "usage": {}, "rating": {}, "quota": {}, "budget": {}, "anomaly": {},
        "integrity": {}
    }

    core = {k: data[k] for k in ["meta", "witness", "usage", "rating", "quota", "budget", "anomaly"]}
    payload = json.dumps(core, ensure_ascii=False, sort_keys=True).encode("utf-8")
    data["integrity"]["signature_sha256"] = hashlib.sha256(payload).hexdigest()

    locked_file = evidence_dir / "evidence-002.locked.json"
    locked_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    index = scan_dir(str(evidence_dir))

    assert index["summary"]["locked"] == 1
    assert index["summary"]["wip"] == 0
    files = index["files"]
    assert files[0]["tier"] == "LOCKED"
    assert files[0]["locked_at"] is not None


def test_evidence_write_index(evidence_dir, sample_evidence):
    """인덱스 파일 생성 테스트"""
    out_path = write_index(str(evidence_dir))

    assert Path(out_path).exists()
    index_data = json.loads(Path(out_path).read_text(encoding="utf-8"))
    assert index_data["summary"]["count"] == 1


def test_evidence_manifest_format(evidence_dir, sample_evidence):
    """manifest.jsonl 형식 테스트"""
    from scripts.ops.evidence_lockdown import write_manifest

    manifest_path = write_manifest(str(evidence_dir))
    manifest_file = Path(manifest_path)

    assert manifest_file.exists()
    lines = manifest_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1

    record = json.loads(lines[0])
    assert "path" in record
    assert "sha256" in record
    assert "tier" in record
    assert "mtime" in record
    assert record["tampered"] is False


def test_evidence_verify_integrity_ok(evidence_dir, sample_evidence):
    """무결성 검증 - 정상"""
    from scripts.ops.evidence_lockdown import verify_integrity

    rc = verify_integrity(str(evidence_dir))
    assert rc == 0


def test_evidence_verify_integrity_fail(evidence_dir, sample_evidence):
    """무결성 검증 - 변조 감지"""
    from scripts.ops.evidence_lockdown import verify_integrity

    # 변조
    data = json.loads(sample_evidence.read_text(encoding="utf-8"))
    data["integrity"]["signature_sha256"] = "invalid"
    sample_evidence.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    rc = verify_integrity(str(evidence_dir))
    assert rc == 1


def test_evidence_missing_keys_tampered(evidence_dir):
    """필수 키 누락 시 변조 판정"""
    incomplete = evidence_dir / "incomplete.json"
    incomplete.write_text(json.dumps({"meta": {}}), encoding="utf-8")

    index = scan_dir(str(evidence_dir))

    files = [f for f in index["files"] if f["path"] == "incomplete.json"]
    assert len(files) == 1
    assert files[0]["tampered"] is True


def test_evidence_multiple_files(evidence_dir):
    """여러 Evidence 파일 스캔"""
    import hashlib
    from datetime import datetime, timezone

    for i in range(3):
        data = {
            "meta": {"tenant": f"test-{i}", "generated_at": datetime.now(timezone.utc).isoformat()},
            "witness": {"csv_sha256": f"abc{i}"},
            "usage": {}, "rating": {}, "quota": {}, "budget": {}, "anomaly": {},
            "integrity": {}
        }
        core = {k: data[k] for k in ["meta", "witness", "usage", "rating", "quota", "budget", "anomaly"]}
        payload = json.dumps(core, ensure_ascii=False, sort_keys=True).encode("utf-8")
        data["integrity"]["signature_sha256"] = hashlib.sha256(payload).hexdigest()

        ev_file = evidence_dir / f"evidence-{i:03d}.json"
        ev_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    index = scan_dir(str(evidence_dir))
    assert index["summary"]["count"] == 3
    assert index["summary"]["tampered"] == 0
