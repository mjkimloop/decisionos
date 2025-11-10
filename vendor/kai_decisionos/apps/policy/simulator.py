from __future__ import annotations

from typing import Dict, List

from apps.policy.models import PolicyRule
from apps.rule_engine.parser import parse_expression


def _match(rule: PolicyRule, payload: Dict) -> bool:
    tree = parse_expression(rule.when)
    ctx = {"payload": payload}
    return bool(eval(compile(tree, filename="<expr>", mode="eval"), {"__builtins__": {}}, ctx))


def simulate(policy: Dict, rows: List[Dict]) -> Dict:
    rules = [PolicyRule(**r) for r in policy.get("rules", [])]
    counts = {"allow": 0, "deny": 0, "review": 0}
    for row in rows:
        decision = "review"
        for r in rules:
            if _match(r, row):
                decision = r.action
                break
        counts[decision] += 1
    n = len(rows)
    return {"n": n, "counts": counts}

