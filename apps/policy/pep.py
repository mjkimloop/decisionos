"""
Policy Enforcement Point (PEP) for RBAC

v0.5.11r-5: 디폴트 디나이 강화
- DEFAULT_ALLOW = False (명시적 최소 권한 원칙)
- Wildcard 매칭 지원 (deploy:* 등)
- Deny 사유 상세 로깅
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache
from typing import Set

# 디폴트 디나이: 명시적 grant 없으면 거부
DEFAULT_ALLOW = False


@lru_cache(maxsize=1)
def _allowed() -> Set[str]:
    """허용된 스코프 목록 반환"""
    scopes = os.getenv("DECISIONOS_ALLOW_SCOPES", "")
    if not scopes.strip():
        # 환경변수 미설정 시 디폴트 디나이
        if DEFAULT_ALLOW:
            return {"*"}
        return set()
    if scopes.strip() == "*":
        return {"*"}
    return {scope.strip() for scope in scopes.split(",") if scope.strip()}


def _matches_wildcard(granted: str, requested: str) -> bool:
    """Wildcard 매칭 지원 (예: deploy:* 는 deploy:promote 허용)"""
    if granted == "*":
        return True
    if granted.endswith(":*"):
        prefix = granted[:-1]  # "deploy:" 까지
        return requested.startswith(prefix)
    return granted == requested


def enforce(scope: str) -> bool:
    """스코프 권한 체크 (True=허용, False=거부)"""
    allowed = _allowed()

    # Wildcard 또는 정확히 일치하는 grant 찾기
    for granted in allowed:
        if _matches_wildcard(granted, scope):
            _audit_log("allow", scope, granted)
            return True

    # 매칭되는 grant 없음 → deny
    _audit_log("deny", scope, None)
    return False


def require(scope: str) -> None:
    """스코프 권한 요구 (없으면 PermissionError 발생)"""
    if not enforce(scope):
        allowed = _allowed()
        if not allowed:
            raise PermissionError(f"RBAC deny: scope={scope}, reason=no_grants_configured")
        raise PermissionError(f"RBAC deny: scope={scope}, reason=no_matching_grant, allowed={sorted(allowed)}")


def _audit_log(decision: str, scope: str, matched_grant: str | None) -> None:
    """RBAC 감사 로그 (stderr)"""
    if matched_grant:
        print(f"[RBAC] {decision}: scope={scope}, grant={matched_grant}", file=sys.stderr)
    else:
        allowed = _allowed()
        grants_str = ",".join(sorted(allowed)) if allowed else "(none)"
        print(f"[RBAC] {decision}: scope={scope}, grants={grants_str}", file=sys.stderr)


__all__ = ["enforce", "require", "DEFAULT_ALLOW"]
