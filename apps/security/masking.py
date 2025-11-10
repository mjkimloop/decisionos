from __future__ import annotations

def mask_phone(value: str) -> str:
    digits = [c for c in value if c.isdigit()]
    if len(digits) < 4:
        return "*" * len(value)
    return "***-****-" + "".join(digits[-4:])


def hash_email(value: str) -> str:
    local, _, domain = value.partition("@")
    if not domain:
        return value
    return f"{local[:2]}***@{domain}"


__all__ = ["mask_phone", "hash_email"]
