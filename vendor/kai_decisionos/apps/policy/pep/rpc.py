from __future__ import annotations

from typing import Any, Dict, Tuple

from apps.catalog.tags import get_dataset
from apps.security.masking import apply_controls, default_controls, merge_controls
PII_CLASSIFICATIONS = {"PII", "PII-S", "RESTRICTED"}


def _resolve_controls(resource: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any] | None]:
    dataset_id = resource.get("dataset_id")
    dataset = get_dataset(str(dataset_id)) if dataset_id else None
    dataset_controls = dataset.controls if dataset else {}
    baseline = default_controls(resource.get("classification"))
    controls = merge_controls(dataset_controls, baseline)
    return controls, (dataset.to_dict() if dataset else None)


def _mask_payload(payload: Dict[str, Any], controls: Dict[str, Any], dataset: Dict[str, Any] | None) -> Dict[str, Any]:
    mutated, _ = apply_controls(
        payload,
        controls,
        metadata={
            "dataset_id": dataset["dataset_id"] if dataset else None,
            "channel": "rpc",
        },
    )
    return mutated


def enforce_rpc(subject: dict, resource: dict, context: dict, payload: Dict[str, Any]) -> Dict[str, Any]:
    from apps.policy.pdp import evaluate

    action = context.get("action") or "read"
    decision = evaluate(subject, action, resource, context)
    if not decision.allow:
        raise PermissionError("policy_denied")

    controls, dataset_dict = _resolve_controls(resource)
    if not any(controls.get(key) for key in ("mask", "hash", "tokenize", "redact")):
        classification = resource.get("classification")
        if classification in PII_CLASSIFICATIONS:
            controls = default_controls(classification)
        else:
            return dict(payload)

    return _mask_payload(dict(payload), controls, dataset_dict)


__all__ = ["enforce_rpc"]
