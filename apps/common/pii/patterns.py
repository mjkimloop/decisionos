from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

_DEFAULT_PROFILE = {
    "version": "v1",
    "patterns": {
        "email": r"(?i)[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}",
        "kr_phone": r"(?:\+82-?)?0?1[0-9]-?\d{3,4}-?\d{4}",
        "rrn_like": r"\d{6}-?\d{7}",
        "card_hint": r"\b\d{4}-\d{4}-\d{4}-\d{4}\b",
    },
    "strategy": {"mode": "mask", "mask": "[REDACTED]"},
    "response_keys": ["message", "detail", "error"],
}


def load_profile(path: str | None = None) -> Dict:
    profile_path = path or os.getenv("DECISIONOS_PII_PROFILE", "configs/pii/profile.json")
    file = Path(profile_path)
    if not file.exists():
        return _DEFAULT_PROFILE
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _DEFAULT_PROFILE
        return data
    except Exception:
        return _DEFAULT_PROFILE
