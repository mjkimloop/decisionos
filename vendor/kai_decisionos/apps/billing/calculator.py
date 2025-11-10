from __future__ import annotations

from typing import Iterable


def calculate_invoice_items(usage_items: Iterable[dict], unit_price: float) -> list[dict]:
    lines: list[dict] = []
    for item in usage_items:
        qty = float(item.get("value", 0))
        amount = round(qty * unit_price, 4)
        lines.append({"metric": item.get("metric", "decision_calls"), "quantity": qty, "unit_price": unit_price, "amount": amount})
    return lines

