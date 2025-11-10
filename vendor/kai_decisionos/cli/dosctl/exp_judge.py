from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
import argparse
import sys
from typing import Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

COMPARISON_PATTERN = re.compile(
    r"^\s*(?P<left>[a-zA-Z_][\w\.]*)\s*(?P<op><=|>=|==|!=|<|>)\s*(?P<right>-?\d+(\.\d+)?)\s*$"
)

SLO_TO_METRIC = {
    "p95_ms": ("latency_p95", "<="),
    "err_rate": ("err_rate", "<="),
    "ai_citation_cov": ("citation_cov", ">="),
    "ag_mapping_loss": ("parity_delta", "<="),
    "cost_krw": ("cost_krw", "<="),
    "latency_p95_delta_pct": ("latency_p95_delta_pct", "<="),
    "err_rate_delta_pp": ("err_rate_delta_pp", "<="),
    "latency_p95_delta_pp": ("latency_p95_delta_pp", "<="),
    "replay_hash_match": ("replay_hash_match", "=="),
    "err_rate_delta_pct": ("err_rate_delta_pct", "<="),
}


@dataclass(frozen=True)
class Comparison:
    left: str
    op: str
    right: float


def parse_expression(expression: str) -> List[Comparison]:
    if not expression:
        raise ValueError("Expression is required")
    parts = [part.strip() for part in re.split(r"\bAND\b", expression, flags=re.IGNORECASE) if part.strip()]
    if not parts:
        raise ValueError("No clauses found in expression")
    comparisons: List[Comparison] = []
    for clause in parts:
        match = COMPARISON_PATTERN.match(clause)
        if not match:
            raise ValueError(f"Invalid clause: {clause}")
        comparisons.append(
            Comparison(
                left=match.group("left"),
                op=match.group("op"),
                right=float(match.group("right")),
            )
        )
    return comparisons


def _compare(op: str, actual: float, expected: float) -> bool:
    if op == "<=":
        return actual <= expected
    if op == "<":
        return actual < expected
    if op == ">=":
        return actual >= expected
    if op == ">":
        return actual > expected
    if op == "==":
        return actual == expected
    if op == "!=":
        return actual != expected
    raise ValueError(f"Unsupported operator: {op}")


def evaluate_expression(comparisons: Iterable[Comparison], metrics: Dict[str, float]) -> Tuple[bool, List[str]]:
    failures: List[str] = []
    for comp in comparisons:
        if comp.left not in metrics:
            failures.append(f"{comp.left} missing")
            continue
        actual = float(metrics[comp.left])
        if not _compare(comp.op, actual, comp.right):
            failures.append(f"{comp.left} {comp.op} {comp.right} (actual={actual})")
    return len(failures) == 0, failures


def build_default_expression(route: Dict) -> str:
    slo = route.get("slo", {})
    clauses: List[str] = []
    for key, (metric, op) in SLO_TO_METRIC.items():
        if key in slo:
            clauses.append(f"{metric} {op} {slo[key]}")
    if not clauses:
        raise ValueError(f"No supported SLO keys for route {route.get('route_id')}")
    return " AND ".join(clauses)


def load_json(path: str | Path) -> Dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_cli_judge(
    witness_path: str | Path,
    slo_path: str | Path,
    output_path: str | Path = "verdicts_cli.json",
) -> Dict[str, Dict[str, object]]:
    witness = load_json(witness_path)
    slo = load_json(slo_path)

    metrics = witness
    results: Dict[str, Dict[str, object]] = {}
    for route in slo.get("routes", []):
        route_id = route["route_id"]
        expression = route.get("dsl") or build_default_expression(route)
        comparisons = parse_expression(expression)
        verdict, failures = evaluate_expression(comparisons, metrics)
        results[route_id] = {
            "expression": expression,
            "verdict": "PASS" if verdict else "FAIL",
            "failures": failures,
        }

    overall = "PASS" if all(v["verdict"] == "PASS" for v in results.values()) else "FAIL"
    payload = {"overall_verdict": overall, "routes": results}
    Path(output_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _run_expr_mode(expression: str, witness_path: str | Path, output_path: str | Path) -> Dict[str, Dict[str, object]]:
    witness = load_json(witness_path)
    comparisons = parse_expression(expression)
    verdict, failures = evaluate_expression(comparisons, witness)
    routes = {
        "ad_hoc": {
            "expression": expression,
            "verdict": "PASS" if verdict else "FAIL",
            "failures": failures,
        }
    }
    payload = {"overall_verdict": "PASS" if verdict else "FAIL", "routes": routes}
    Path(output_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate witness JSON via DSL or slo.json")
    parser.add_argument("--witness", required=True, help="Path to witness JSON")
    parser.add_argument("--slo", default="configs/slo/slo.json", help="Path to slo.json")
    parser.add_argument("--expr", help="Ad-hoc DSL expression (bypass slo routes)")
    parser.add_argument("--output", default="verdicts_cli.json", help="Output JSON path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.expr:
        _run_expr_mode(args.expr, args.witness, args.output)
    else:
        run_cli_judge(args.witness, args.slo, args.output)


if __name__ == "__main__":
    main()


__all__ = [
    "Comparison",
    "parse_expression",
    "evaluate_expression",
    "build_default_expression",
    "run_cli_judge",
    "load_json",
]
