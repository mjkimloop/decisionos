"""PII redaction rules with soft/hard mode support.

Provides regex-based PII detection and masking for:
- Email addresses
- Phone numbers (Korean format)
- Resident Registration Numbers (RRN)
- Credit card numbers
- Addresses (Korean format)

Modes:
- soft: Partial masking (e.g., "a***@example.com")
- hard: Full redaction (e.g., "[REDACTED_EMAIL]")
"""
from __future__ import annotations

import os
import re
from typing import Any, Tuple

# Regex patterns
EMAIL = re.compile(r"([A-Za-z0-9._%+-])([A-Za-z0-9._%+-]*)(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PHONE = re.compile(r"\b(\+?82-?|0)(\d{2,3})-(\d{3,4})-(\d{4})\b")
RRN = re.compile(r"\b(\d{6})-(\d)(\d{6})\b")
CARD4 = re.compile(r"\b(\d{4})[- ]?(\d{4})[- ]?(\d{4})[- ]?(\d{4})\b")
ADDR1 = re.compile(
    r"(?:서울|인천|부산|대구|대전|광주|울산|경기|강원|충북|충남|경북|경남|전북|전남|제주)[^\s,]{1,10}(로|길)\s?\d{1,4}"
)


def pii_mode() -> str:
    """Get current PII mode from environment."""
    return os.getenv("DECISIONOS_PII_MODE", "soft").lower()  # soft|hard


# Masking functions
def _mask_email_soft(m):
    first, rest, dom = m.groups()
    return f"{first}{'*' * max(1, len(rest))}{dom}"


def _mask_email_hard(m):
    return "[REDACTED_EMAIL]"


def _mask_phone_soft(m):
    cc, a, b, c = m.groups()
    return f"{cc}{a}-***-{c}"


def _mask_phone_hard(m):
    return "[REDACTED_PHONE]"


def _mask_rrn_soft(m):
    a, b, c = m.groups()
    return f"{a}-{b}{'*' * 6}"


def _mask_rrn_hard(m):
    return "[REDACTED_RRN]"


def _mask_card_soft(m):
    a, b, c, d = m.groups()
    return f"{a}-****-****-{d}"


def _mask_card_hard(m):
    return "[REDACTED_CARD]"


def _mask_addr_soft(m):
    s = m.group(0)
    return s[: max(2, len(s) // 3)] + "***"


def _mask_addr_hard(m):
    return "[REDACTED_ADDR]"


def mask_text_with_count(s: str) -> Tuple[str, int]:
    """Mask PII in text and return (masked_text, count).

    Args:
        s: Input text

    Returns:
        Tuple of (masked text, number of PII items masked)
    """
    mode = pii_mode()
    count = 0

    repl_email = _mask_email_soft if mode == "soft" else _mask_email_hard
    repl_phone = _mask_phone_soft if mode == "soft" else _mask_phone_hard
    repl_rrn = _mask_rrn_soft if mode == "soft" else _mask_rrn_hard
    repl_card = _mask_card_soft if mode == "soft" else _mask_card_hard
    repl_addr = _mask_addr_soft if mode == "soft" else _mask_addr_hard

    def sub_count(pat, func, txt):
        nonlocal count
        matches = 0

        def replacer(m):
            nonlocal matches
            matches += 1
            return func(m)

        txt = pat.sub(replacer, txt)
        count += matches
        return txt

    s = sub_count(EMAIL, repl_email, s)
    s = sub_count(PHONE, repl_phone, s)
    s = sub_count(RRN, repl_rrn, s)
    s = sub_count(CARD4, repl_card, s)
    s = sub_count(ADDR1, repl_addr, s)

    return s, count


def mask_obj_with_stats(obj: Any) -> Tuple[Any, int]:
    """Recursively mask PII in objects and return (masked_obj, total_count).

    Args:
        obj: Any JSON-serializable object

    Returns:
        Tuple of (masked object, total number of PII items masked)
    """
    total = 0

    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            vv, c = mask_obj_with_stats(v)
            total += c
            out[k] = vv
        return out, total

    if isinstance(obj, list):
        out = []
        for x in obj:
            xx, c = mask_obj_with_stats(x)
            total += c
            out.append(xx)
        return out, total

    if isinstance(obj, str):
        s, c = mask_text_with_count(obj)
        return s, c

    return obj, 0
