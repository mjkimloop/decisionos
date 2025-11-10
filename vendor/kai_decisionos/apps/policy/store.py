from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .parser import PolicyRule, parse_policy

SEMVER_RE = re.compile(r"^v\d+\.\d+\.\d+$")


@dataclass
class PolicyMetadata:
    version: str
    approved_by: str
    summary: Optional[str] = None


@dataclass
class PolicyBundle:
    policies: List[PolicyRule] = field(default_factory=list)
    metadata: Optional[PolicyMetadata] = None


class PolicyStore:
    def __init__(self) -> None:
        self._policies: Dict[str, PolicyBundle] = {}

    def apply_bundle(self, name: str, bundle_text: str, metadata: Optional[Dict[str, str]] = None) -> None:
        bundle_meta = self._coerce_metadata(metadata)
        from .pdp import validate_rule  # local import to avoid circular dependency

        policies = [parse_policy(block) for block in bundle_text.split("---") if block.strip()]
        for policy in policies:
            validate_rule(policy)
        self._policies[name] = PolicyBundle(policies=policies, metadata=bundle_meta)

    def list_policies(self) -> Dict[str, PolicyBundle]:
        return self._policies

    def clear(self) -> None:
        self._policies.clear()

    @staticmethod
    def _coerce_metadata(meta: Optional[Dict[str, str]]) -> PolicyMetadata:
        if not meta:
            raise ValueError("metadata_required")
        version = (meta.get("version") or "").strip()
        if not SEMVER_RE.match(version):
            raise ValueError("invalid_version")
        approved_by = (meta.get("approved_by") or "").strip()
        if not approved_by:
            raise ValueError("approved_by_required")
        summary = (meta.get("summary") or "").strip() or None
        return PolicyMetadata(version=version, approved_by=approved_by, summary=summary)


STORE = PolicyStore()

__all__ = ["PolicyBundle", "PolicyMetadata", "PolicyStore", "STORE"]
