from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Set


@dataclass
class NetworkPolicy:
    allow_all: bool = False
    allowed_domains: Set[str] = field(default_factory=set)

    @classmethod
    def deny_all(cls) -> "NetworkPolicy":
        return cls(allow_all=False, allowed_domains=set())


def enforce_network_policy(policy: NetworkPolicy, manifest_rules: dict) -> None:
    if policy.allow_all:
        return
    requested = set(manifest_rules.get("egress", {}).get("allow", []))
    disallowed = requested - policy.allowed_domains
    if disallowed:
        raise PermissionError(f"egress_not_allowed:{','.join(sorted(disallowed))}")


__all__ = ["NetworkPolicy", "enforce_network_policy"]
