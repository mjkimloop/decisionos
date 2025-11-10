from __future__ import annotations

import hashlib
from typing import Any, Dict, Iterable, List, Tuple

from . import tokenization


def mask_phone(value: str) -> str:
    digits = [c for c in value if c.isdigit()]
    if len(digits) <= 4:
        return "*" * len(value)
    return "***-****-" + "".join(digits[-4:])


def _mask_last4(value: str) -> str:
    if not value:
        return value
    tail = value[-4:]
    return f"{'*' * max(len(value) - 4, 0)}{tail}"


def _mask_name(value: str) -> str:
    if not value:
        return value
    return value[0] + "*" * (len(value) - 1)


def hash_email(value: str) -> str:
    local, _, domain = value.partition("@")
    if not domain:
        return value
    return f"{local[:2]}***@{domain}"


def hash_value(value: str, length: int = 12) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest[:length]


def mask_value(value: str, strategy: str) -> str:
    strategy = (strategy or "").lower()
    if strategy in {"phone", "tel"}:
        return mask_phone(value)
    if strategy in {"email", "mail", "hash_email"}:
        return hash_email(value)
    if strategy in {"last4", "suffix"}:
        return _mask_last4(value)
    if strategy in {"name", "initial"}:
        return _mask_name(value)
    if strategy in {"full", "all"}:
        return "*" * len(value)
    if strategy.startswith("prefix"):
        try:
            keep = int(strategy.replace("prefix", ""))
        except ValueError:
            keep = 2
        return value[:keep] + "*" * max(len(value) - keep, 0)
    return "***"


def apply_controls(record: Dict[str, Any], controls: Dict[str, Any], *, metadata: Dict[str, Any] | None = None) -> Tuple[Dict[str, Any], List[str]]:
    """Apply masking/tokenisation/hashing controls to a record."""
    metadata = metadata or {}
    mutated = dict(record)
    actions: List[str] = []
    mask_config = controls.get("mask", {})
    for field, strategy in mask_config.items():
        if field in mutated and mutated[field] is not None:
            mutated[field] = mask_value(str(mutated[field]), strategy)
            actions.append(f"mask:{field}:{strategy}")

    for field in controls.get("hash", []):
        if field in mutated and mutated[field] is not None:
            mutated[field] = hash_value(str(mutated[field]))
            actions.append(f"hash:{field}")

    for field in controls.get("tokenize", []):
        if field in mutated and mutated[field] is not None:
            token = tokenization.tokenize(
                str(mutated[field]),
                metadata={
                    "field": field,
                    "strategy": "tokenize",
                    **metadata,
                },
            )
            mutated[field] = token
            actions.append(f"tokenize:{field}")

    for field in controls.get("redact", []):
        if field in mutated:
            mutated[field] = "[REDACTED]"
            actions.append(f"redact:{field}")

    return mutated, actions


def merge_controls(*control_sets: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {"mask": {}, "hash": [], "tokenize": [], "redact": []}
    for controls in control_sets:
        if not controls:
            continue
        merged["mask"].update(controls.get("mask", {}))
        merged["hash"].extend(controls.get("hash", []))
        merged["tokenize"].extend(controls.get("tokenize", []))
        merged["redact"].extend(controls.get("redact", []))
        if controls.get("require_purpose"):
            merged["require_purpose"] = True
        if controls.get("max_export_days") is not None:
            merged["max_export_days"] = controls["max_export_days"]
    # normalise unique lists
    for key in ("hash", "tokenize", "redact"):
        unique: List[str] = []
        for val in merged[key]:
            if val not in unique:
                unique.append(val)
        merged[key] = unique
    return merged


def default_controls(classification: str | None) -> Dict[str, Any]:
    if classification and classification.upper() in {"PII", "PII-S", "RESTRICTED"}:
        return {
            "mask": {"phone": "phone", "email": "email"},
            "tokenize": [],
            "hash": [],
            "redact": [],
        }
    return {}


__all__ = [
    "apply_controls",
    "default_controls",
    "hash_email",
    "hash_value",
    "mask_phone",
    "mask_value",
    "merge_controls",
]
