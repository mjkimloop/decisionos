"""
RBAC 디폴트 디나이 정책 테스트 (v0.5.11r-5)

최소 권한 원칙:
- DEFAULT_ALLOW = False
- 명시적 grant 없으면 403
- Wildcard 매칭 지원
- Deny 사유 로깅
"""
import pytest
import os
from apps.policy.pep import enforce, require, DEFAULT_ALLOW, _allowed

pytestmark = [pytest.mark.gate_ah]

def test_rbac_default_deny_constant():
    """DEFAULT_ALLOW가 False로 설정되어 있는지 확인"""
    assert DEFAULT_ALLOW is False, "DEFAULT_ALLOW must be False for default deny"

def test_rbac_no_grants_deny(monkeypatch):
    """grant 없을 시 deny"""
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "")
    _allowed.cache_clear()

    assert not enforce("deploy:promote")
    with pytest.raises(PermissionError, match="no_grants_configured"):
        require("deploy:promote")

def test_rbac_exact_match_allow(monkeypatch):
    """정확히 일치하는 grant는 허용"""
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "deploy:promote")
    _allowed.cache_clear()

    assert enforce("deploy:promote")
    require("deploy:promote")  # 예외 없음

def test_rbac_exact_match_deny(monkeypatch):
    """다른 스코프는 거부"""
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "deploy:promote")
    _allowed.cache_clear()

    assert not enforce("deploy:rollback")
    with pytest.raises(PermissionError, match="no_matching_grant"):
        require("deploy:rollback")

def test_rbac_wildcard_star(monkeypatch):
    """'*' grant는 모든 스코프 허용"""
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "*")
    _allowed.cache_clear()

    assert enforce("deploy:promote")
    assert enforce("deploy:rollback")
    assert enforce("any:scope")

def test_rbac_wildcard_prefix(monkeypatch):
    """'deploy:*' grant는 deploy: 접두사 모두 허용"""
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "deploy:*")
    _allowed.cache_clear()

    assert enforce("deploy:promote")
    assert enforce("deploy:rollback")
    assert enforce("deploy:canary")
    assert not enforce("judge:run")
    assert not enforce("ops:read")

def test_rbac_multiple_grants(monkeypatch):
    """여러 grant 중 하나라도 매칭되면 허용"""
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "judge:run,deploy:promote,ops:read")
    _allowed.cache_clear()

    assert enforce("judge:run")
    assert enforce("deploy:promote")
    assert enforce("ops:read")
    assert not enforce("deploy:rollback")

def test_rbac_mixed_wildcard_and_exact(monkeypatch):
    """Wildcard와 정확 매칭 혼용"""
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "deploy:*,judge:run")
    _allowed.cache_clear()

    assert enforce("deploy:promote")
    assert enforce("deploy:rollback")
    assert enforce("judge:run")
    assert not enforce("judge:evaluate")
    assert not enforce("ops:read")

def test_rbac_whitespace_handling(monkeypatch):
    """공백 처리"""
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", " deploy:promote , judge:run ")
    _allowed.cache_clear()

    assert enforce("deploy:promote")
    assert enforce("judge:run")

def test_rbac_empty_string_vs_unset(monkeypatch):
    """빈 문자열과 미설정 모두 deny"""
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "")
    _allowed.cache_clear()
    assert not enforce("deploy:promote")

    monkeypatch.delenv("DECISIONOS_ALLOW_SCOPES", raising=False)
    _allowed.cache_clear()
    assert not enforce("deploy:promote")

def test_rbac_error_message_details(monkeypatch):
    """에러 메시지에 deny 사유 포함"""
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "judge:run")
    _allowed.cache_clear()

    with pytest.raises(PermissionError) as exc_info:
        require("deploy:promote")

    err_msg = str(exc_info.value)
    assert "deploy:promote" in err_msg
    assert "no_matching_grant" in err_msg
    assert "judge:run" in err_msg

def test_rbac_deny_when_no_grants(monkeypatch, capsys):
    """grant 없을 때 deny 로그 확인"""
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "")
    _allowed.cache_clear()

    result = enforce("deploy:promote")
    assert result is False

    captured = capsys.readouterr()
    assert "[RBAC] deny" in captured.err
    assert "deploy:promote" in captured.err

def test_rbac_allow_log(monkeypatch, capsys):
    """grant 있을 때 allow 로그 확인"""
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "deploy:promote")
    _allowed.cache_clear()

    result = enforce("deploy:promote")
    assert result is True

    captured = capsys.readouterr()
    assert "[RBAC] allow" in captured.err
    assert "deploy:promote" in captured.err
