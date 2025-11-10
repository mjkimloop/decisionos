from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Action = Literal["allow", "deny", "review"]


@dataclass
class PolicyRule:
    when: str
    action: Action
    reason: str | None = None


@dataclass
class Policy:
    name: str
    rules: list[PolicyRule]

