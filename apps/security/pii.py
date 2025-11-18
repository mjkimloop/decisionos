from __future__ import annotations

from typing import Any, Dict

from apps.common.pii import build_masker, mask_event as _mask_event, mask_text as _mask_text


class Redactor:
    """Legacy-compatible redactor backed by the common masker."""

    def __init__(self) -> None:
        self._masker = build_masker()

    def redact_text(self, text: str) -> str:
        return self._masker.mask_text(text)

    def redact_json(self, obj: Any) -> Any:
        return self._masker.mask_event(obj)


PIIRedactor = Redactor


def get_redactor() -> PIIRedactor:
    return PIIRedactor()


def redact_text(text: str) -> str:
    return _mask_text(text)


def redact_dict(obj: Dict[str, Any]) -> Dict[str, Any]:
    return _mask_event(obj)


def redact_string(value: str) -> str:
    return redact_text(value)


__all__ = [
    "Redactor",
    "PIIRedactor",
    "get_redactor",
    "redact_text",
    "redact_dict",
    "redact_string",
]
