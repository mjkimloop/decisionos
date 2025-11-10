from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

from apps.catalog.tags import get_dataset
from apps.security.masking import apply_controls, default_controls, merge_controls

PII_CLASSIFICATIONS = {"PII", "PII-S", "RESTRICTED"}


def _resolve_controls(resource: Dict[str, object]) -> Tuple[Dict[str, object], Dict[str, object] | None]:
    dataset_id = resource.get("dataset_id")
    dataset = get_dataset(str(dataset_id)) if dataset_id else None
    dataset_controls = dataset.controls if dataset else {}
    classification = resource.get("classification")
    baseline = default_controls(str(classification) if classification else None)
    controls = merge_controls(dataset_controls, baseline)
    return controls, (dataset.to_dict() if dataset else None)


def enforce_sql(subject: dict, resource: dict, query: str, rows: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    from apps.policy.pdp import evaluate

    decision = evaluate(subject, "read", resource, {"channel": "sql", "query": query})
    if not decision.allow:
        raise PermissionError("policy_denied")

    materialized = [dict(row) for row in rows]
    controls, dataset_dict = _resolve_controls(resource)

    if not any(controls.get(key) for key in ("mask", "hash", "tokenize", "redact")):
        if resource.get("classification") in PII_CLASSIFICATIONS:
            controls = default_controls(resource.get("classification"))
        else:
            return materialized

    mutated: List[Dict[str, object]] = []
    for row in materialized:
        masked_row, _ = apply_controls(
            row,
            controls,
            metadata={
                "dataset_id": dataset_dict["dataset_id"] if dataset_dict else None,
                "channel": "sql",
            },
        )
        mutated.append(masked_row)
    return mutated


__all__ = ["enforce_sql"]
