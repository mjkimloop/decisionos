from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .tags import DatasetTags, get_dataset


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class BoundaryEvent:
    dataset_id: str
    org_id: str
    reason: str
    severity: str = "high"
    required_controls: List[str] = field(default_factory=list)
    purpose: str | None = None
    ticket_id: str | None = None
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BoundaryResult:
    dataset_id: str
    org_id: str
    residency: str | None
    target_region: str | None
    enforced_controls: List[str] = field(default_factory=list)
    tags: Dict[str, Any] = field(default_factory=dict)
    status: str = "ok"


_EVENT_LOG: List[BoundaryEvent] = []


class BoundaryViolation(Exception):
    def __init__(self, reason: str, *, required_controls: Optional[List[str]] = None, event: Optional[BoundaryEvent] = None):
        super().__init__(reason)
        self.reason = reason
        self.required_controls = required_controls or []
        self.event = event


def _record_event(event: BoundaryEvent) -> BoundaryEvent:
    _EVENT_LOG.append(event)
    return event


def evaluate_boundary(
    dataset_id: str,
    *,
    org_id: str,
    target_region: str | None = None,
    purpose: str | None = None,
    ticket_id: str | None = None,
    retention_days: int | None = None,
    context: Optional[Dict[str, Any]] = None,
) -> BoundaryResult:
    dataset: DatasetTags | None = get_dataset(dataset_id)
    if not dataset:
        raise BoundaryViolation("dataset_not_tagged", required_controls=["catalog.tag_required"])

    org_region = (org_id.split(":", 1)[0] or "").upper()
    residency = (dataset.residency or "").upper() or None
    requested_region = (target_region or org_region or residency or "").upper() or None

    enforced_controls: List[str] = []
    details = {"org_region": org_region, "requested_region": requested_region}

    # Residency strictness: dataset residency must match request or be explicitly allowed.
    if residency and requested_region and residency != requested_region:
        allowed = {region.upper() for region in dataset.allowed_regions}
        if requested_region not in allowed:
            event = _record_event(
                BoundaryEvent(
                    dataset_id=dataset_id,
                    org_id=org_id,
                    reason="residency_mismatch",
                    required_controls=["policy.override", "dpa.record"],
                    purpose=purpose,
                    ticket_id=ticket_id,
                    context=details | (context or {}),
                )
            )
            raise BoundaryViolation("residency_violation", required_controls=event.required_controls, event=event)

    # High risk data requires explicit purpose/ticket for exports.
    high_risk = dataset.restricted or dataset.pii or (dataset.classification or "").upper() in {"PII-S", "RESTRICTED"}
    exporting = residency and requested_region and residency != requested_region
    if high_risk and exporting:
        missing_controls: List[str] = []
        if not purpose:
            missing_controls.append("purpose.binding")
        if not ticket_id:
            missing_controls.append("ticket_id")
        if dataset.controls.get("require_purpose") and not purpose:
            missing_controls.append("policy.purpose_required")
        max_days = dataset.controls.get("max_export_days")
        if max_days is not None and retention_days:
            try:
                max_days_int = int(max_days)
                if retention_days > max_days_int:
                    missing_controls.append(f"retention<=${max_days_int}")
            except (TypeError, ValueError):
                missing_controls.append("retention.policy_config_error")
        if missing_controls:
            event = _record_event(
                BoundaryEvent(
                    dataset_id=dataset_id,
                    org_id=org_id,
                    reason="export_controls_missing",
                    required_controls=missing_controls,
                    purpose=purpose,
                    ticket_id=ticket_id,
                    context=details | (context or {}),
                )
            )
            raise BoundaryViolation("export_control_violation", required_controls=missing_controls, event=event)
        enforced_controls.extend(["export.logged", "purpose.bound", "ticket.captured"])

    # Additional controls derived from dataset configuration.
    controls = dataset.controls
    if controls.get("tokenize"):
        enforced_controls.append("tokenize:" + ",".join(controls["tokenize"]))
    if controls.get("mask"):
        enforced_controls.append("mask:" + ",".join(sorted(controls["mask"].keys())))

    return BoundaryResult(
        dataset_id=dataset_id,
        org_id=org_id,
        residency=residency,
        target_region=requested_region,
        enforced_controls=enforced_controls,
        tags=dataset.to_dict(),
        status="ok",
    )


def list_events() -> List[Dict[str, Any]]:
    return [event.to_dict() for event in _EVENT_LOG]


def clear_events() -> None:
    _EVENT_LOG.clear()


__all__ = [
    "BoundaryEvent",
    "BoundaryResult",
    "BoundaryViolation",
    "evaluate_boundary",
    "list_events",
    "clear_events",
]
