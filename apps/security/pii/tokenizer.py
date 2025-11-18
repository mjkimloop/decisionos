"""
PII Tokenization - HMAC-based non-reversible token generation.

Tokens format: TKN:{type}:{hash8}
"""
import hmac
import hashlib
import os


def token_of(value: str, pii_type: str) -> str:
    """
    Generate non-reversible token for PII value.

    Args:
        value: Original PII value
        pii_type: Type of PII (e.g., "mobile_phone", "email")

    Returns:
        Token string: "TKN:{type}:{hash8}"

    Requires:
        DECISIONOS_PII_TOKEN_KEY environment variable
    """
    key_str = os.environ.get("DECISIONOS_PII_TOKEN_KEY")
    if not key_str:
        raise ValueError("DECISIONOS_PII_TOKEN_KEY environment variable required")

    key = key_str.encode("utf-8")
    message = f"{pii_type}|{value}".encode("utf-8")

    h = hmac.new(key, message, hashlib.sha256).hexdigest()[:8]

    return f"TKN:{pii_type}:{h}"
