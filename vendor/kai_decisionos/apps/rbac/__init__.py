"""RBAC scaffolding for Gate-N."""

from .roles import assign_role, revoke_role, list_roles, check_permission, ROLE_PERMISSIONS

__all__ = [
    "assign_role",
    "revoke_role",
    "list_roles",
    "check_permission",
    "ROLE_PERMISSIONS",
]

