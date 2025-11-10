"""
tests/e2e/test_promote_controller_hook_v1.py

E2E 스모크: promote.sh + controller_hook 통합
"""
import os, json, subprocess, pytest
from pathlib import Path

pytestmark = [pytest.mark.e2e]


def test_promote_runs_hook():
    """promote.sh 실행 시 controller_hook이 호출되고 마커 생성"""
    # 환경 설정
    os.environ["DECISIONOS_CONTROLLER_HOOK"] = "python -m apps.experiment.controller_hook"
    os.environ["DECISIONOS_ENFORCE_RBAC"] = "0"  # 테스트에서는 RBAC 비활성화
    
    # promote.sh 실행
    repo = Path.cwd()
    rc = subprocess.run(
        ["bash", "pipeline/release/promote.sh"],
        cwd=repo,
        capture_output=True,
        text=True
    ).returncode
    
    assert rc == 0, "promote.sh should succeed"
    
    # 결과 확인
    stage_file = Path("var/rollout/desired_stage.txt")
    assert stage_file.exists(), "Stage file should be created"
    assert stage_file.read_text().strip() == "promote"
    
    # 훅 로그 확인
    hook_log = Path("var/rollout/hooks.log")
    assert hook_log.exists(), "Hook log should be created"
    log_content = hook_log.read_text(encoding="utf-8")
    assert "stage=promote" in log_content
    assert "source=promote.sh" in log_content
    
    # 마커 파일 확인
    marker = Path("var/rollout/last_hook.json")
    assert marker.exists(), "Hook marker should be created"
    data = json.loads(marker.read_text(encoding="utf-8"))
    assert data["stage"] == "promote"
    assert data["source"] == "promote.sh"
    assert "ts" in data


def test_promote_with_custom_stage():
    """커스텀 stage (canary) 지정"""
    os.environ["DECISIONOS_CONTROLLER_HOOK"] = "python -m apps.experiment.controller_hook"
    os.environ["DECISIONOS_ENFORCE_RBAC"] = "0"
    
    repo = Path.cwd()
    rc = subprocess.run(
        ["bash", "pipeline/release/promote.sh", "canary"],
        cwd=repo,
        capture_output=True,
        text=True
    ).returncode
    
    assert rc == 0
    
    stage_file = Path("var/rollout/desired_stage.txt")
    assert stage_file.read_text().strip() == "canary"
    
    marker = Path("var/rollout/last_hook.json")
    data = json.loads(marker.read_text(encoding="utf-8"))
    assert data["stage"] == "canary"
