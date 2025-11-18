"""
PII Redactor with regex pattern matching and Luhn validation for credit cards.

Supports Korean context PII: resident ID, phone numbers, credit cards, etc.
"""
import json
import re
from typing import Dict, Any, List, Tuple
from .tokenizer import token_of


def build_patterns(cfg: dict) -> List[Tuple[str, re.Pattern, dict]]:
    """
    Build compiled regex patterns from configuration.

    Returns:
        List of (pii_type, pattern, rule) tuples
    """
    pats = []
    for pii_type, rule in cfg.items():
        pattern = re.compile(rule["pattern"])
        pats.append((pii_type, pattern, rule))
    return pats


def luhn_ok(s: str) -> bool:
    """
    Validate credit card number using Luhn algorithm.

    Args:
        s: Credit card number (with or without spaces/dashes)

    Returns:
        True if valid, False otherwise
    """
    # Extract digits only
    digits = [int(c) for c in re.sub(r"[^0-9]", "", s)]

    if len(digits) < 13:
        return False

    checksum = 0
    alt = False

    for d in reversed(digits):
        if alt:
            d = d * 2
            if d > 9:
                d = d - 9
        checksum += d
        alt = not alt

    return checksum % 10 == 0


def redact_text(text: str, cfg: dict, mode: str = "token") -> str:
    """
    Redact PII from text using pattern matching.

    Args:
        text: Input text
        cfg: PII patterns configuration
        mode: "token" or "mask"

    Returns:
        Redacted text with tokens/masks
    """
    pats = build_patterns(cfg)

    def repl(m: re.Match, pii_type: str, rule: dict) -> str:
        """Replace match with token or mask"""
        s = m.group(0)

        # Special handling for credit cards (Luhn validation)
        if pii_type == "credit_card" and rule.get("luhn", False):
            if not luhn_ok(s):
                # Not a valid credit card, don't tokenize
                return s

        if mode == "token":
            return token_of(s, pii_type)
        else:
            return f"[REDACTED:{pii_type}]"

    # Apply all patterns
    for pii_type, pat, rule in pats:
        text = pat.sub(lambda m: repl(m, pii_type, rule), text)

    return text
