from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
import ast
import yaml

# 얇은 래퍼: 기존 engine 구현을 재노출


ALLOWED_AST_NODES = (
    ast.Expression,
    ast.BoolOp,
    ast.BinOp,
    ast.UnaryOp,
    ast.Compare,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Attribute,
    ast.Call,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.Is,
    ast.IsNot,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
)


def safe_eval_guard(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_AST_NODES):
            raise ValueError(f"Disallowed expression node: {type(node).__name__}")
        if isinstance(node, ast.Attribute):
            if not (isinstance(node.value, ast.Name) and node.value.id == "payload" and node.attr == "get"):
                raise ValueError("Only payload.get is allowed")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Attribute):
                raise ValueError("Only attribute calls allowed")
            attr = node.func
            if not (isinstance(attr.value, ast.Name) and attr.value.id == "payload" and attr.attr == "get"):
                raise ValueError("Only payload.get calls allowed")
            if any(kw for kw in getattr(node, "keywords", []) or []):
                raise ValueError("No keyword args allowed")
            for arg in node.args:
                if not isinstance(arg, ast.Constant):
                    raise ValueError("payload.get args must be constants")


@dataclass
class Rule:
    name: str
    when: str
    action: dict
    priority: int = 0
    stop: bool = False


@dataclass
class RuleSet:
    name: str
    version: str
    rules: List[Rule]

    @staticmethod
    def load(path: str | Path) -> "RuleSet":
        p = Path(path)
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        rules = [Rule(**r) for r in data.get("rules", [])]
        return RuleSet(name=data.get("name", p.stem), version=str(data.get("version", "0")), rules=rules)


def parse_ruleset(path: str | Path) -> RuleSet:
    return RuleSet.load(path)


# Backward-compatible alias
def load_ruleset(path: str | Path) -> RuleSet:
    return parse_ruleset(path)


def parse_expression(expr: str) -> ast.AST:
    tree = ast.parse(expr, mode="eval")
    safe_eval_guard(tree)
    return tree
