from __future__ import annotations

import ast
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, List, Tuple

from .parser import PolicyRule
from .store import STORE


@dataclass
class RuleEvaluation:
    policy_ref: str
    effect: str
    priority: int
    matched: bool
    when_result: bool | None = None
    unless_result: bool | None = None
    purpose: str | None = None
    error: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    bundle: str | None = None


@dataclass
class Decision:
    allow: bool
    effect: str
    policy_id: str | None = None
    reason: str | None = None
    purpose: str | None = None
    bundle: str | None = None
    trace: List[RuleEvaluation] = field(default_factory=list)


def evaluate(subject: Dict[str, Any], action: str, resource: Dict[str, Any], context: Dict[str, Any]) -> Decision:
    trace: List[RuleEvaluation] = []
    candidates = _candidate_policies(action)

    for priority, order, bundle_name, policy, metadata in candidates:
        effect = getattr(policy, "effect", "allow")
        policy_ref = policy.policy_id or f"{bundle_name}:{order}"
        result = _assess_policy(policy, subject, action, resource, context)
        evaluation = RuleEvaluation(
            policy_ref=policy_ref,
            effect=effect,
            priority=getattr(policy, "priority", priority),
            matched=result["matched"],
            when_result=result["when_result"],
            unless_result=result["unless_result"],
            purpose=getattr(policy, "purpose", None),
            error=result["error"],
            metadata=metadata,
            bundle=bundle_name,
        )
        trace.append(evaluation)

        if result["error"] or not result["matched"]:
            continue

        if effect == "deny":
            return Decision(
                allow=False,
                effect="deny",
                policy_id=policy_ref,
                reason="explicit_deny",
                purpose=evaluation.purpose,
                bundle=bundle_name,
                trace=trace,
            )

        return Decision(
            allow=True,
            effect="allow",
            policy_id=policy_ref,
            purpose=evaluation.purpose,
            bundle=bundle_name,
            trace=trace,
        )

    return Decision(
        allow=False,
        effect="deny",
        reason="deny_by_default",
        trace=trace,
    )


def _assess_policy(
    policy: PolicyRule,
    subject: Dict[str, Any],
    action: str,
    resource: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    try:
        when_result = _eval_expression(policy.when, subject, action, resource, context)
    except Exception as exc:  # pragma: no cover - defensive, compilation pre-validates
        return {"matched": False, "when_result": None, "unless_result": None, "error": f"when_error:{exc}"}

    if not when_result:
        return {"matched": False, "when_result": False, "unless_result": None, "error": None}

    unless_result: bool | None = None
    if policy.unless:
        try:
            unless_result = _eval_expression(policy.unless, subject, action, resource, context)
        except Exception as exc:  # pragma: no cover - defensive
            return {"matched": False, "when_result": True, "unless_result": None, "error": f"unless_error:{exc}"}
        if unless_result:
            return {"matched": False, "when_result": True, "unless_result": True, "error": None}

    return {
        "matched": True,
        "when_result": True,
        "unless_result": unless_result if unless_result is not None else False,
        "error": None,
    }


def _candidate_policies(action: str) -> List[Tuple[int, int, str, PolicyRule, Dict[str, Any]]]:
    records: List[Tuple[int, int, str, PolicyRule, Dict[str, Any]]] = []
    for bundle_name, bundle in STORE.list_policies().items():
        for order, policy in enumerate(bundle.policies):
            policy_action = getattr(policy, "action", None)
            if policy_action not in (action, "*"):
                continue
            combined_meta: Dict[str, Any] = {}
            if bundle.metadata:
                combined_meta.update(bundle.metadata.__dict__)
            combined_meta.update(getattr(policy, "metadata", {}))
            records.append((getattr(policy, "priority", 0), order, bundle_name, policy, combined_meta))
    records.sort(key=lambda item: (-item[0], 0 if getattr(item[3], "effect", "allow") == "deny" else 1, item[1]))
    return records


_ALLOWED_NAMES = {"subject", "action", "resource", "context", "True", "False", "None"}
_ALLOWED_FUNCS = {"len": len, "any": any, "all": all, "set": set}
_ALLOWED_METHODS = {
    "get",
    "startswith",
    "endswith",
    "lower",
    "upper",
    "intersection",
    "issubset",
    "issuperset",
    "contains",
}
_ALLOWED_BOOL_OPS = (ast.And, ast.Or)
_ALLOWED_UNARY_OPS = (ast.Not,)
_ALLOWED_CMP_OPS = (
    ast.Eq,
    ast.NotEq,
    ast.In,
    ast.NotIn,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.Is,
    ast.IsNot,
)
_ALLOWED_BIN_OPS = (ast.Add, ast.Sub)


def _validate_node(node: ast.AST) -> None:
    if isinstance(node, ast.Expression):
        _validate_node(node.body)
    elif isinstance(node, ast.BoolOp):
        if not isinstance(node.op, _ALLOWED_BOOL_OPS):
            raise ValueError("unsupported_bool_operator")
        for value in node.values:
            _validate_node(value)
    elif isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, _ALLOWED_UNARY_OPS):
            raise ValueError("unsupported_unary_operator")
        _validate_node(node.operand)
    elif isinstance(node, ast.Compare):
        _validate_node(node.left)
        for comparator in node.comparators:
            _validate_node(comparator)
        for op in node.ops:
            if not isinstance(op, _ALLOWED_CMP_OPS):
                raise ValueError("unsupported_comparator")
    elif isinstance(node, ast.Name):
        if node.id not in _ALLOWED_NAMES:
            raise ValueError("name_not_allowed")
    elif isinstance(node, ast.Constant):
        return
    elif isinstance(node, ast.Subscript):
        _validate_node(node.value)
        _validate_node(node.slice)
    elif isinstance(node, ast.Attribute):
        if node.attr.startswith("__"):
            raise ValueError("dunder_attribute_not_allowed")
        _validate_node(node.value)
    elif isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name):
            if func.id not in _ALLOWED_FUNCS:
                raise ValueError("function_not_allowed")
        elif isinstance(func, ast.Attribute):
            if func.attr.startswith("__") or func.attr not in _ALLOWED_METHODS:
                raise ValueError("method_not_allowed")
            _validate_node(func.value)
        else:
            raise ValueError("call_not_allowed")
        for arg in node.args:
            _validate_node(arg)
        for kw in node.keywords:
            _validate_node(kw.value)
    elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        for elt in node.elts:
            _validate_node(elt)
    elif isinstance(node, ast.Dict):
        for key in node.keys:
            if key is not None:
                _validate_node(key)
        for value in node.values:
            _validate_node(value)
    elif isinstance(node, ast.BinOp):
        if not isinstance(node.op, _ALLOWED_BIN_OPS):
            raise ValueError("binary_operator_not_allowed")
        _validate_node(node.left)
        _validate_node(node.right)
    elif node is None:
        return
    else:
        raise ValueError("unsupported_expression")


@lru_cache(maxsize=256)
def _compile_expression(expr: str):
    tree = ast.parse(expr.replace("&&", " and ").replace("||", " or "), mode="eval")
    _validate_node(tree)
    return compile(tree, "<policy_expr>", "eval")


def _eval_expression(expr: str, subject: dict, action: str, resource: dict, context: dict) -> bool:
    if not expr:
        return True
    code = _compile_expression(expr)
    namespace: Dict[str, Any] = {
        "subject": subject,
        "action": action,
        "resource": resource,
        "context": context,
        **_ALLOWED_FUNCS,
    }
    return bool(eval(code, {"__builtins__": {}}, namespace))


def validate_rule(rule: PolicyRule) -> None:
    _compile_expression(rule.when or "True")
    if rule.unless:
        _compile_expression(rule.unless)


__all__ = ["Decision", "RuleEvaluation", "evaluate", "validate_rule"]
