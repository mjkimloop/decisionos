"""
Test PR Playbook Annotation v1
PR 코멘트에 플레이북 주입 테스트
"""
import pytest
from apps.alerts.dispatcher import get_playbook_actions, load_playbooks


@pytest.mark.skip(reason="E2E test - requires GitHub API access")
def test_playbook_in_comment():
    """PR 코멘트에 reason→action 매핑 포함"""
    # This would test the actual PR comment generation
    # Skipped for now as it requires GitHub API access
    pass


def test_get_playbook_actions_exact_match():
    """정확한 reason 매칭"""
    playbooks = {
        "reason:infra-latency:p95": ["Scale out API pods", "Enable cache layer"],
        "reason:budget-burn": ["Freeze rollout", "Reduce canary traffic"],
        "default": ["Open incident ticket"]
    }

    actions = get_playbook_actions("reason:infra-latency:p95", playbooks)
    assert len(actions) == 2
    assert "Scale out API pods" in actions


def test_get_playbook_actions_default():
    """기본 액션 반환"""
    playbooks = {
        "reason:infra-latency:p95": ["Scale out API pods"],
        "default": ["Open incident ticket", "Notify on-call"]
    }

    actions = get_playbook_actions("unknown:reason", playbooks)
    assert len(actions) == 2
    assert "Open incident ticket" in actions
    assert "Notify on-call" in actions
