from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Set


@dataclass
class PermissionSet:
    granted: Set[str] = field(default_factory=set)

    def allows(self, scope: str) -> bool:
        if scope.endswith(".*"):
            return any(s.startswith(scope[:-1]) for s in self.granted)
        return scope in self.granted


def require_permissions(granted: PermissionSet, requested: Iterable[str]) -> None:
    missing = []
    for scope in requested:
        if not granted.allows(scope) and scope not in granted.granted:
            missing.append(scope)
    if missing:
        raise PermissionError(f"missing_permissions:{','.join(missing)}")


__all__ = ["PermissionSet", "require_permissions"]
