from __future__ import annotations

from typing import Dict

from apps.policy.models import PolicyRule
from apps.rule_engine.parser import parse_expression


def enforce(stage: str, policy: Dict, payload: Dict) -> Dict:
    rules = [PolicyRule(**r) for r in policy.get("rules", [])]
    for r in rules:
        try:
            tree = parse_expression(r.when)
            if bool(eval(compile(tree, filename="<expr>", mode="eval"), {"__builtins__": {}}, {"payload": payload})):
                return {"stage": stage, "action": r.action, "reason": r.reason}
        except Exception:
            continue
    return {"stage": stage, "action": "allow"}

