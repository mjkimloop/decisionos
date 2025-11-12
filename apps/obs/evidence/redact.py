"""
PII Redaction Pipeline
민감 정보 마스킹/해싱/제거
"""
from __future__ import annotations
import hashlib
import os
import re
from typing import Any, Dict, Literal

RedactStrategy = Literal["mask", "hash", "remove"]


def load_redaction_rules(config_path: str = "configs/redaction/fields.yaml") -> Dict[str, Dict[str, Any]]:
    """Load PII redaction rules from YAML config"""
    if not os.path.exists(config_path):
        return {}

    import yaml
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    return cfg.get("fields", {})


def mask_email(email: str) -> str:
    """Mask email: a****@example.com"""
    if "@" not in email:
        return "****"

    local, domain = email.split("@", 1)
    if len(local) <= 1:
        masked_local = "*"
    else:
        masked_local = local[0] + "****"

    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    """Mask phone: ***-****-1234"""
    # Remove all non-digits
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 4:
        return "****"

    return "***-****-" + digits[-4:]


def hash_value(value: str, salt: str = "") -> str:
    """Hash value with optional salt"""
    if not salt:
        salt = os.environ.get("DECISIONOS_HASH_SALT", "default-salt")

    data = f"{value}{salt}".encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:16]


def redact_field(field_name: str, value: Any, strategy: RedactStrategy, salt_ref: str = "") -> Any:
    """Redact single field based on strategy"""
    if value is None or value == "":
        return value

    value_str = str(value)

    if strategy == "remove":
        return None
    elif strategy == "mask":
        if field_name == "email":
            return mask_email(value_str)
        elif field_name == "phone":
            return mask_phone(value_str)
        else:
            # Generic masking: first char + ****
            return value_str[0] + "****" if len(value_str) > 1 else "****"
    elif strategy == "hash":
        salt = ""
        if salt_ref.startswith("ENV:"):
            env_key = salt_ref[4:]
            salt = os.environ.get(env_key, "")
        return hash_value(value_str, salt)

    return value


def redact_dict(data: Dict[str, Any], rules: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Recursively redact dictionary fields"""
    if not rules:
        return data

    result = {}
    for key, value in data.items():
        if key in rules:
            rule = rules[key]
            strategy = rule.get("strategy", "mask")
            salt_ref = rule.get("salt_ref", "")
            result[key] = redact_field(key, value, strategy, salt_ref)
        elif isinstance(value, dict):
            result[key] = redact_dict(value, rules)
        elif isinstance(value, list):
            result[key] = [redact_dict(item, rules) if isinstance(item, dict) else item for item in value]
        else:
            result[key] = value

    return result


def redact_evidence(evidence: Dict[str, Any], config_path: str = "configs/redaction/fields.yaml") -> Dict[str, Any]:
    """
    Redact PII fields in evidence

    Args:
        evidence: Evidence dictionary
        config_path: Path to redaction rules config

    Returns:
        Redacted evidence dictionary
    """
    rules = load_redaction_rules(config_path)
    if not rules:
        return evidence

    return redact_dict(evidence, rules)
