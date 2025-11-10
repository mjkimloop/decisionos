from __future__ import annotations

import re

PII_PATTERNS = [
    re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b"),  # SSN-like
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    re.compile(r"\b\d{10,16}\b"),  # generic digits
]


def anonymize_text(text: str) -> str:
    out = text
    for pat in PII_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out


def anonymize_record(rec: dict) -> dict:
    masked = {}
    for k, v in rec.items():
        if isinstance(v, str):
            masked[k] = anonymize_text(v)
        else:
            masked[k] = v
    return masked

