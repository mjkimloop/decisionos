from __future__ import annotations

import copy
import os
import re
from typing import Any, Dict, Iterable

from .patterns import load_profile


class PIIMasker:
    def __init__(
        self,
        *,
        allowlist: Iterable[str] | None = None,
        mask_token: str | None = None,
    ) -> None:
        profile = load_profile()
        self._mask = mask_token or os.getenv("DECISIONOS_PII_MASK_TOKEN", profile.get("strategy", {}).get("mask", "[REDACTED]"))
        self._allow = {k.strip() for k in (allowlist or []) if k.strip()}
        patterns = profile.get("patterns", {})
        self._regex = [(name, re.compile(pattern)) for name, pattern in patterns.items() if pattern]

    def mask_text(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        out = text
        for _, regex in self._regex:
            out = regex.sub(self._mask, out)
        return out

    def _mask_value(self, key: str, value: Any) -> Any:
        if key in self._allow:
            return value
        return self.mask_event(value)

    def mask_event(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            masked: Dict[str, Any] = {}
            for k, v in obj.items():
                masked[k] = self._mask_value(k, v)
            return masked
        if isinstance(obj, list):
            return [self.mask_event(v) for v in obj]
        if isinstance(obj, str):
            return self.mask_text(obj)
        return obj


def build_masker() -> PIIMasker:
    allow = os.getenv("DECISIONOS_PII_ALLOWLIST", "")
    allowlist = [tok.strip() for tok in allow.split(",") if tok.strip()]
    return PIIMasker(allowlist=allowlist)


def mask_text(text: str) -> str:
    return build_masker().mask_text(text)


def mask_event(event: Dict[str, Any]) -> Dict[str, Any]:
    return build_masker().mask_event(copy.deepcopy(event))
