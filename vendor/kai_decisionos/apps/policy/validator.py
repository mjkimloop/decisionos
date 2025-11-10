from __future__ import annotations

from typing import List, Dict

from apps.policy.models import Policy, PolicyRule
from apps.rule_engine.parser import parse_expression


def validate_policy(data: Dict) -> Dict:
    issues: List[str] = []
    if not isinstance(data, dict):
        return {"valid": False, "issues": ["policy must be object"]}
    name = data.get("name")
    rules = data.get("rules", []) or []
    if not name:
        issues.append("missing name")
    if not isinstance(rules, list) or not rules:
        issues.append("no rules")
    for i, r in enumerate(rules):
        w = (r or {}).get("when")
        act = (r or {}).get("action")
        if not isinstance(w, str) or not w.strip():
            issues.append(f"rule[{i}] missing when")
        else:
            try:
                parse_expression(w)
            except Exception as e:  # pragma: no cover
                issues.append(f"rule[{i}] invalid when: {e}")
        if act not in {"allow", "deny", "review"}:
            issues.append(f"rule[{i}] invalid action")
    return {"valid": len(issues) == 0, "issues": issues}

