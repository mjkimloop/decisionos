from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

import yaml

from .parser import PolicyRule, parse_policy


@dataclass
class PolicyBundle:
    metadata: Dict[str, Any] = field(default_factory=dict)
    policies: List[PolicyRule] = field(default_factory=list)


class PolicyStore:
    def __init__(self) -> None:
        self._policies: Dict[str, PolicyBundle] = {}

    def apply_bundle(self, name: str, bundle_text: str) -> None:
        sections = [block.strip() for block in bundle_text.split("---") if block.strip()]
        metadata: Dict[str, Any] = {}
        policies: List[PolicyRule] = []
        for idx, block in enumerate(sections):
            if idx == 0 and block.lower().startswith("meta:"):
                try:
                    parsed_meta = yaml.safe_load(block) or {}
                    metadata = parsed_meta.get("meta", parsed_meta)
                    continue
                except yaml.YAMLError as exc:  # pragma: no cover - bubble up as ValueError
                    raise ValueError(f"invalid_policy_metadata: {exc}") from exc
            policies.append(parse_policy(block))
        self._policies[name] = PolicyBundle(metadata=metadata, policies=policies)

    def list_policies(self) -> Dict[str, PolicyBundle]:
        return self._policies

    def clear(self) -> None:
        self._policies.clear()


STORE = PolicyStore()

__all__ = ["PolicyBundle", "PolicyStore", "STORE"]
