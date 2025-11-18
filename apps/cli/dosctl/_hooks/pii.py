from __future__ import annotations

import os
from typing import Any

from apps.common.pii import build_masker


def apply_pii(obj: Any) -> Any:
    if os.getenv("DECISIONOS_PII_ENABLE", "0") != "1":
        return obj
    masker = build_masker()
    if isinstance(obj, str):
        return masker.mask_text(obj)
    if isinstance(obj, dict):
        return masker.mask_event(obj)
    if isinstance(obj, list):
        return [apply_pii(v) for v in obj]
    return obj
