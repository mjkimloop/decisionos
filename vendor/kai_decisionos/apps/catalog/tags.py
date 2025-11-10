from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DatasetTags:
    dataset_id: str
    residency: str | None = None
    classification: str | None = None
    pii: bool = False
    finance: bool = False
    restricted: bool = False
    owner_org: str | None = None
    allowed_regions: List[str] = field(default_factory=list)
    controls: Dict[str, Any] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        # provide convenient aliases for downstream callers
        payload["tags"] = dict(self.attributes)
        return payload


_TAG_REGISTRY: Dict[str, DatasetTags] = {}


def _coerce_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        if not value:
            return []
        return [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]
    if isinstance(value, Iterable):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _normalise_controls(tags: Dict[str, Any]) -> Dict[str, Any]:
    controls = tags.get("controls") or {}
    if not isinstance(controls, dict):
        controls = {}
    result: Dict[str, Any] = {
        "mask": {},
        "tokenize": [],
        "hash": [],
        "redact": [],
        "require_purpose": bool(tags.get("require_purpose") or controls.get("require_purpose")),
        "max_export_days": tags.get("max_export_days") or controls.get("max_export_days"),
    }

    if "mask" in controls and isinstance(controls["mask"], dict):
        result["mask"] = {str(k): str(v) for k, v in controls["mask"].items()}
    if "tokenize" in controls:
        result["tokenize"] = _coerce_list(controls["tokenize"])
    if "hash" in controls:
        result["hash"] = _coerce_list(controls["hash"])
    if "redact" in controls:
        result["redact"] = _coerce_list(controls["redact"])

    return result


def tag_dataset(dataset_id: str, tags: Dict[str, Any], *, owner_org: str | None = None) -> DatasetTags:
    """Create or update dataset catalog tags with derived attributes."""
    if not dataset_id:
        raise ValueError("dataset_id required")
    existing = _TAG_REGISTRY.get(dataset_id)
    base_attrs = dict(existing.attributes) if existing else {}
    base_attrs.update(tags)

    residency = str(tags.get("residency") or base_attrs.get("residency") or "").upper() or None
    classification = tags.get("classification") or base_attrs.get("classification")
    pii_flag = bool(tags.get("pii") if "pii" in tags else base_attrs.get("pii"))
    finance_flag = bool(tags.get("finance") if "finance" in tags else base_attrs.get("finance"))
    restricted_flag = bool(
        tags.get("restricted") if "restricted" in tags else base_attrs.get("restricted")
    )
    allowed_regions = _coerce_list(tags.get("allowed_regions") or base_attrs.get("allowed_regions"))
    controls = _normalise_controls(tags if tags else base_attrs)

    record = DatasetTags(
        dataset_id=dataset_id,
        residency=residency,
        classification=classification,
        pii=pii_flag,
        finance=finance_flag,
        restricted=restricted_flag or (classification or "").upper() in {"PII-S", "RESTRICTED"},
        owner_org=owner_org or (existing.owner_org if existing else None),
        allowed_regions=allowed_regions,
        controls=controls,
        attributes=base_attrs,
        created_at=existing.created_at if existing else _now(),
        updated_at=_now(),
    )
    _TAG_REGISTRY[dataset_id] = record
    return record


def get_dataset(dataset_id: str) -> Optional[DatasetTags]:
    return _TAG_REGISTRY.get(dataset_id)


def get_tags(dataset_id: str) -> Dict[str, Any]:
    dataset = get_dataset(dataset_id)
    return dataset.to_dict() if dataset else {}


def list_datasets() -> List[Dict[str, Any]]:
    return [record.to_dict() for record in _TAG_REGISTRY.values()]


def clear_registry() -> None:
    _TAG_REGISTRY.clear()


__all__ = [
    "DatasetTags",
    "tag_dataset",
    "get_dataset",
    "get_tags",
    "list_datasets",
    "clear_registry",
]
