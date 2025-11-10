from __future__ import annotations

from typing import Dict, Set


ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "admin": {"*"},
    "finance": {"billing.read", "billing.write", "payments.manage"},
    "analyst": {"analytics.read", "feedback.read"},
    "agent": {"cases.read", "cases.write"},
    "developer": {"packs.read", "packs.deploy"},
}

USER_ROLES: Dict[str, Set[str]] = {}


def assign_role(user: str, role: str) -> None:
    USER_ROLES.setdefault(user, set()).add(role)


def revoke_role(user: str, role: str) -> None:
    USER_ROLES.setdefault(user, set()).discard(role)


def list_roles(user: str) -> Set[str]:
    return USER_ROLES.get(user, set())


def check_permission(user: str, permission: str) -> bool:
    roles = USER_ROLES.get(user, set())
    for role in roles:
        perms = ROLE_PERMISSIONS.get(role, set())
        if "*" in perms or permission in perms:
            return True
        parts = permission.split(".")
        for i in range(1, len(parts)):
            prefix = ".".join(parts[:i]) + ".*"
            if prefix in perms:
                return True
    return False


__all__ = ["ROLE_PERMISSIONS", "assign_role", "revoke_role", "list_roles", "check_permission"]

