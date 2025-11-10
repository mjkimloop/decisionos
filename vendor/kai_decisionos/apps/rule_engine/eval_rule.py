from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, Dict

from .engine import RuleSet, evaluate_rules


def introspect_ast(expr: str) -> dict:
    """Parse expression and return AST node types for debugging."""
    try:
        tree = ast.parse(expr, mode="eval")
        nodes = [type(node).__name__ for node in ast.walk(tree)]
        return {"valid": True, "nodes": nodes}
    except Exception as e:
        return {"valid": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Evaluate a rule YAML against payload JSON")
    parser.add_argument("path", type=str, help="Path to YAML ruleset")
    parser.add_argument("payload", type=str, help="Path to payload JSON file or '-' for stdin")
    parser.add_argument("--show-ast", action="store_true", help="Show AST introspection for each rule")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    rs = RuleSet.load(args.path)

    if args.payload == "-":
        data: Dict[str, Any] = json.load(sys.stdin)
    else:
        data = json.loads(Path(args.payload).read_text(encoding="utf-8"))

    # Optionally show AST introspection
    if args.show_ast:
        ast_info = {}
        for rule in rs.rules:
            ast_info[rule.name] = introspect_ast(rule.when)
        print("=== AST Introspection ===")
        print(json.dumps(ast_info, indent=2))
        print()

    # Evaluate rules
    out = evaluate_rules(rs, data)

    # Add metadata to output
    result = {
        "ruleset": {"name": rs.name, "version": rs.version},
        "outcome": out,
        "total_rules": len(rs.rules),
        "rules_evaluated": len([r for r in out.get("rules_applied", []) if not r.startswith("ERROR:")])
    }

    # Print result
    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


if __name__ == "__main__":
    main()

