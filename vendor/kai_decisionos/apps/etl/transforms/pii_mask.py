from __future__ import annotations

from typing import Dict, Any

SENSITIVE_KEYS = {"ssn", "phone", "email"}


def mask(record: Dict[str, Any]) -> Dict[str, Any]:
    result = record.copy()
    for key in SENSITIVE_KEYS:
        if key in result:
            result[key] = "***MASKED***"
    return result


__all__ = ["mask", "SENSITIVE_KEYS"]
