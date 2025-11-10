from __future__ import annotations

from typing import Any, Dict, List
import ast

from .parser import Rule, RuleSet

ALLOWED_AST_NODES = {
    ast.Expression,
    ast.BoolOp,
    ast.UnaryOp,
    ast.Compare,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.Attribute,
    ast.Call,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.Gt,
    ast.LtE,
    ast.GtE,
}


def _validate_node(node: ast.AST) -> None:
    if type(node) not in ALLOWED_AST_NODES:
        raise ValueError(f"Disallowed AST node: {type(node).__name__}")

    for child in ast.iter_child_nodes(node):
        _validate_node(child)

    if isinstance(node, ast.Attribute):
        if not (isinstance(node.value, ast.Name) and node.value.id == "payload" and node.attr == "get"):
            raise ValueError("Only payload.get() calls allowed")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Attribute):
            raise ValueError("Only attribute method calls allowed")
        if not (isinstance(node.func.value, ast.Name) and node.func.value.id == "payload" and node.func.attr == "get"):
            raise ValueError("Only payload.get() calls allowed")
        if node.keywords:
            raise ValueError("Keyword arguments not allowed")
        for arg in node.args:
            if not isinstance(arg, ast.Constant):
                raise ValueError("payload.get arguments must be constants")


def safe_eval(expression: str, context: Dict[str, Any]) -> Any:
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise SyntaxError("Invalid expression syntax") from exc

    _validate_node(tree)

    try:
        compiled = compile(tree, "<rule_expr>", "eval")
        return eval(compiled, {"__builtins__": {}}, context)
    except Exception as exc:
        raise ValueError(f"Evaluation error: {exc}") from exc


def evaluate_rule(rule: Rule, payload: Dict[str, Any]) -> bool:
    try:
        return bool(safe_eval(rule.when, {"payload": payload}))
    except Exception as exc:
        raise ValueError(f"Failed to evaluate rule {rule.name}: {exc}") from exc


def evaluate_rules(ruleset: RuleSet, payload: Dict[str, Any]) -> dict:
    results: List[str] = []
    outcome = {"class": "review", "reasons": [], "confidence": 0.5, "required_docs": []}
    ordered = sorted(ruleset.rules, key=lambda r: (-int(getattr(r, "priority", 0))))
    for rule in ordered:
        try:
            ok = evaluate_rule(rule, payload)
            if ok:
                results.append(rule.name)
                for k, v in rule.action.items():
                    if k == "reasons" and isinstance(v, list):
                        outcome.setdefault("reasons", [])
                        outcome["reasons"] = list({*outcome["reasons"], *v})
                    elif k == "required_docs" and isinstance(v, list):
                        outcome.setdefault("required_docs", [])
                        outcome["required_docs"] = list({*outcome["required_docs"], *v})
                    else:
                        outcome[k] = v
                if getattr(rule, "stop", False):
                    break
        except Exception as exc:
            results.append(f"ERROR:{rule.name}:{exc}")
    outcome["rules_applied"] = results
    return outcome


def introspect_expression(expression: str) -> Dict[str, Any]:
    try:
        tree = ast.parse(expression, mode="eval")
        _validate_node(tree)
        node_names = sorted({type(node).__name__ for node in ast.walk(tree)})
        return {"valid": True, "nodes": node_names, "error": None}
    except Exception as exc:
        return {"valid": False, "nodes": [], "error": str(exc)}


__all__ = [
    "safe_eval",
    "evaluate_rule",
    "evaluate_rules",
    "introspect_expression",
    "ALLOWED_AST_NODES",
]
