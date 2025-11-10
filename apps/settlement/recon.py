from __future__ import annotations

from typing import Iterable, List, Tuple


def reconcile(ledger: Iterable[dict], settlement_rows: Iterable[dict]) -> Tuple[List[dict], List[dict]]:
    ledger_map = {row["charge_id"]: row for row in ledger}
    settlement_map = {row["charge_id"]: row for row in settlement_rows}

    missing: List[dict] = []
    extra: List[dict] = []

    for charge_id, entry in ledger_map.items():
        if charge_id not in settlement_map:
            missing.append(entry)
        else:
            if entry["amount"] != settlement_map[charge_id]["amount"]:
                missing.append({"charge_id": charge_id, "ledger_amount": entry["amount"], "settlement_amount": settlement_map[charge_id]["amount"]})

    for charge_id, entry in settlement_map.items():
        if charge_id not in ledger_map:
            extra.append(entry)

    return missing, extra


__all__ = ["reconcile"]
