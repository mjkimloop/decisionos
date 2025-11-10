from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Dict, Any, Optional

from apps.etl.transforms.cleanse import cleanse
from apps.etl.transforms.pii_mask import mask
from apps.etl.transforms.map_ontology import map_fields
from apps.ingest.idempotency import store


@dataclass
class PipelineStep:
    name: str
    fn: Callable[[Dict[str, Any]], Dict[str, Any]]


DEFAULT_STEPS = [
    PipelineStep("cleanse", cleanse),
    PipelineStep("mask", mask),
    PipelineStep("map", map_fields),
]


def run_pipeline(
    records: List[Dict[str, Any]],
    steps: List[PipelineStep] | None = None,
    policy_guard: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    steps = DEFAULT_STEPS if steps is None else steps
    output: List[Dict[str, Any]] = []
    for rec in records:
        key = rec.get("id") or rec.get("uuid")
        if key and not store.check_and_set(str(key)):
            continue
        transformed = rec
        for step in steps:
            transformed = step.fn(transformed)
        if policy_guard:
            transformed = policy_guard(transformed)
        output.append(transformed)
    return output


__all__ = ["PipelineStep", "run_pipeline"]
