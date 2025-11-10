from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

DEFAULT_RULES = {
    "KR": {"vat_rate": 0.1, "exempt": []},
    "US": {"vat_rate": 0.0, "exempt": ["digital_goods"]},
}


def load_rules(path: Path | None = None) -> Dict[str, dict]:
    if path is None or not path.exists():
        return DEFAULT_RULES
    return json.loads(path.read_text(encoding="utf-8"))


def calculate_tax(amount: int, region_code: str, category: str | None = None, rules: Dict[str, dict] | None = None) -> int:
    rules = rules or DEFAULT_RULES
    rule = rules.get(region_code, {"vat_rate": 0.0, "exempt": []})
    if category and category in rule.get("exempt", []):
        return 0
    rate = rule.get("vat_rate", 0.0)
    return int(amount * rate)


__all__ = ["load_rules", "calculate_tax"]
