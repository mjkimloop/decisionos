"""
Rule Engine - Backward Compatibility Layer
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from packages.common.config import settings
from .parser import Rule, RuleSet, load_ruleset
from .evaluator import evaluate_rules as eval_rules_impl, safe_eval as safe_eval_impl

__all__ = [
    "Rule",
    "RuleSet",
    "evaluate_rules",
    "load_rules_for_contract",
    "load_contract",
    "safe_eval",
]


def evaluate_rules(ruleset: RuleSet, payload: Dict[str, Any]) -> dict:
    return eval_rules_impl(ruleset, payload)


def safe_eval(expression: str, context: Dict[str, Any]) -> Any:
    return safe_eval_impl(expression, context)


def load_contract(contract: str) -> dict:
    base = Path(__file__).resolve().parents[2]  # kai-decisionos/
    candidates = [
        Path(settings.contracts_dir) / f"{contract}.contract.json",
        Path(settings.data_dir) / "contracts" / f"{contract}.contract.json",
        Path("packages/contracts") / f"{contract}.contract.json",
        base / "packages" / "contracts" / f"{contract}.contract.json",
    ]
    for contract_path in candidates:
        if contract_path.exists():
            data = json.loads(contract_path.read_text(encoding="utf-8"))
            return data
    raise FileNotFoundError(f"Contract file not found for {contract}")


def load_rules_for_contract(contract: str) -> RuleSet:
    c = load_contract(contract)
    rule_path = c.get("rule_path")
    if not rule_path:
        raise FileNotFoundError("Contract missing rule_path")
    base = Path(__file__).resolve().parents[2]
    candidates = [
        Path(settings.data_dir) / Path(rule_path),
        base / Path(rule_path),
        base / Path(settings.data_dir) / Path(rule_path),
    ]
    for p in candidates:
        if p.exists():
            return load_ruleset(p)
    raise FileNotFoundError(f"Rules file not found: {rule_path}")
