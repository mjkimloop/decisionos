from __future__ import annotations

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def _allowed() -> set[str]:
    scopes = os.getenv("DECISIONOS_ALLOW_SCOPES", "")
    if scopes.strip() == "*":
        return {"*"}
    return {scope.strip() for scope in scopes.split(",") if scope.strip()}


def enforce(scope: str) -> bool:
    allowed = _allowed()
    if "*" in allowed:
        return True
    return scope in allowed


def require(scope: str) -> None:
    if not enforce(scope):
        raise PermissionError(f"RBAC deny: scope={scope}")


__all__ = ["enforce", "require"]
