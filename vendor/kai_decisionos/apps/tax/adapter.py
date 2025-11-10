from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

PRESETS_PATH = Path(__file__).with_name("presets_kr_eu.yaml")


@dataclass
class TaxComputation:
    tax_total: int
    currency: str
    breakdown: list[dict]

    def model_dump(self) -> dict:
        return {"tax_total": self.tax_total, "currency": self.currency, "breakdown": self.breakdown}


class TaxAdapter:
    def __init__(self, rules: Optional[Dict[str, Any]] = None) -> None:
        self.rules = rules or self._load_rules()

    def _load_rules(self) -> Dict[str, Any]:
        if not PRESETS_PATH.exists():
            return {}
        data = yaml.safe_load(PRESETS_PATH.read_text(encoding="utf-8")) or {}
        return {k.upper(): v for k, v in data.items()}

    def calculate(
        self,
        *,
        amount: int,
        country: str = "KR",
        category: str = "default",
        tax_exempt: bool = False,
        metadata: Optional[dict] = None,
    ) -> TaxComputation:
        rules = self.rules.get(country.upper(), {})
        if tax_exempt:
            return TaxComputation(tax_total=0, currency=rules.get("currency", "KRW"), breakdown=[])
        rates = rules.get("categories", {})
        rate = rates.get(category, rules.get("default_rate", 0.0))
        tax_total = round(amount * rate)
        breakdown = [
            {
                "label": rules.get("label", "VAT"),
                "rate": rate,
                "amount": tax_total,
                "meta": metadata or {},
            }
        ]
        return TaxComputation(tax_total=tax_total, currency=rules.get("currency", "KRW"), breakdown=breakdown)

    def to_json(self) -> str:
        return json.dumps(self.rules, indent=2)


@lru_cache(maxsize=1)
def get_adapter() -> TaxAdapter:
    return TaxAdapter()


__all__ = ["TaxAdapter", "get_adapter", "TaxComputation"]
