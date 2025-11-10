from __future__ import annotations

from typing import Any, Dict, Set

from .models import ORGS


DEFAULT_PLANS: dict[str, dict[str, Any]] = {
    "free": {
        "entitlements": {"catalog.read", "lineage.read", "decisions.run.basic"},
        "quotas": {"decisions_per_day": 200},
    },
    "growth": {
        "entitlements": {"catalog.*", "lineage.*", "decisions.run", "pipelines.run", "guardrails.v2"},
        "quotas": {"decisions_per_day": 10000},
    },
    "pro": {
        "entitlements": {"catalog.*", "lineage.*", "decisions.run", "pipelines.run", "guardrails.v2", "hitl.basic"},
        "quotas": {"decisions_per_day": 5000},
    },
    "enterprise": {
        "entitlements": {"*"},
        "quotas": {"decisions_per_day": 200000},
    },
}

ENTITLEMENT_OVERRIDES: Dict[str, Set[str]] = {}


def set_plan_for_org(org_id: str, plan: str) -> None:
    org = ORGS.get(org_id)
    if not org:
        raise KeyError("org_not_found")
    org.plan = plan


def grant_entitlement(org_id: str, feature: str) -> None:
    ENTITLEMENT_OVERRIDES.setdefault(org_id, set()).add(feature)


def revoke_entitlement(org_id: str, feature: str) -> None:
    ENTITLEMENT_OVERRIDES.setdefault(org_id, set()).discard(feature)


def list_effective_entitlements(org_id: str) -> Set[str]:
    org = ORGS.get(org_id)
    plan_name = org.plan if org else "free"
    plan = DEFAULT_PLANS.get(plan_name, DEFAULT_PLANS["free"])  # type: ignore[index]
    ents: Set[str] = set(plan.get("entitlements", set()))
    ents.update(ENTITLEMENT_OVERRIDES.get(org_id, set()))
    return ents


def check_entitlement(org_id: str, feature: str) -> bool:
    org = ORGS.get(org_id)
    if not org:
        return False
    plan = DEFAULT_PLANS.get(org.plan, DEFAULT_PLANS["free"])  # type: ignore[index]
    ents: set[str] = set(plan.get("entitlements", set()))
    ents.update(ENTITLEMENT_OVERRIDES.get(org_id, set()))
    if "*" in ents:
        return True
    if feature in ents:
        return True
    # wildcard prefix match like "catalog.*"
    parts = feature.split(".")
    for i in range(1, len(parts)):
        prefix = ".".join(parts[:i]) + ".*"
        if prefix in ents:
            return True
    return False


__all__ = [
    "DEFAULT_PLANS",
    "ENTITLEMENT_OVERRIDES",
    "set_plan_for_org",
    "grant_entitlement",
    "revoke_entitlement",
    "list_effective_entitlements",
    "check_entitlement",
]
