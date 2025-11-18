import json
import importlib
import pytest

pytestmark = [pytest.mark.gate_ah]

@pytest.fixture(autouse=True)
def stage_key(monkeypatch):
    monkeypatch.setenv("DECISIONOS_STAGE_KEY", "test-key")
    monkeypatch.setenv("DECISIONOS_STAGE_KEY_ID", "test")

def test_canary_auto_promote_promote_exit(tmp_path, monkeypatch):
    # 3연속 통과 + burst 0 → promote
    ev = {
        "canary": {
            "windows": [
                {"pass": True, "burst": 0},
                {"pass": True, "burst": 0},
                {"pass": True, "burst": 0},
            ]
        }
    }
    latest = tmp_path / "latest.json"
    latest.write_text(json.dumps(ev), encoding="utf-8")

    # 환경 설정 및 모듈 리로드
    monkeypatch.setenv("DECISIONOS_EVIDENCE_LATEST", str(latest))
    monkeypatch.setenv("DECISIONOS_AUTOPROMOTE_ENABLE", "1")
    monkeypatch.setenv("DECISIONOS_CANARY_REQUIRED_PASSES", "3")
    monkeypatch.setenv("DECISIONOS_CANARY_MAX_BURST", "0")

    import jobs.canary_auto_promote as cap
    importlib.reload(cap)

    # stage 파일 쓰기는 테스트에서 무해화 (원자 기록 유틸을 노옵으로 패치)
    monkeypatch.setattr(cap, "write_stage_atomic", lambda token, path=None: None)

    with pytest.raises(SystemExit) as se:
        cap.main()
    assert se.value.code == 0  # promote → exit 0
