from __future__ import annotations

from typing import Dict, Any


def cleanse(record: Dict[str, Any]) -> Dict[str, Any]:
    return {k: (v.strip() if isinstance(v, str) else v) for k, v in record.items()}


__all__ = ["cleanse"]
