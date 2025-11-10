from __future__ import annotations

from typing import Any, Dict, List

from apps.executor.pipeline import simulate as executor_simulate
from .schema import PackSpec


def simulate_pack(spec: PackSpec, rows: List[Dict[str, Any]], label_key: str | None = None) -> Dict[str, Any]:
    label = label_key or "converted"
    results: Dict[str, Any] = {"pack": spec.identifier(), "contracts": {}, "n": len(rows)}
    for contract in spec.contracts:
        try:
            metrics = executor_simulate(contract, rows, label)
        except Exception as exc:  # noqa: BLE001 simple scaffold
            metrics = {"error": str(exc)}
        results["contracts"][contract] = metrics
    return results


__all__ = ["simulate_pack"]

