"""
Test PII Redaction Pipeline (gate_t)
"""
import pytest
from apps.obs.evidence.redact import (
    mask_email,
    mask_phone,
    hash_value,
    redact_field,
    redact_dict,
    redact_evidence,
    load_redaction_rules,
)


@pytest.mark.gate_t
def test_mask_email():
    """Test email masking strategy"""
    assert mask_email("user@example.com") == "u****@example.com"
    assert mask_email("john.doe@company.org") == "j****@company.org"
    assert mask_email("a@b.com") == "*@b.com"  # Single char email
    # Invalid email - returns ****
    assert mask_email("not-an-email") == "****"


@pytest.mark.gate_t
def test_mask_phone():
    """Test phone masking strategy"""
    assert mask_phone("010-1234-5678") == "***-****-5678"
    assert mask_phone("02-123-4567") == "***-****-4567"
    assert mask_phone("1234567890") == "***-****-7890"  # Always adds dashes
    # Invalid phone - returns ****
    assert mask_phone("abc") == "****"


@pytest.mark.gate_t
def test_hash_value():
    """Test hash strategy with salt"""
    salt = "test-salt"
    hashed1 = hash_value("sensitive-data", salt)
    hashed2 = hash_value("sensitive-data", salt)
    hashed3 = hash_value("different-data", salt)

    # Same input + salt = same hash
    assert hashed1 == hashed2
    # Different input = different hash
    assert hashed1 != hashed3
    # Hash should be hex string (truncated to 16 chars)
    assert len(hashed1) == 16


@pytest.mark.gate_t
def test_redact_field_mask():
    """Test field redaction with mask strategy"""
    assert redact_field("email", "user@example.com", "mask") == "u****@example.com"
    assert redact_field("phone", "010-1234-5678", "mask") == "***-****-5678"
    assert redact_field("other", "value", "mask") == "v****"


@pytest.mark.gate_t
def test_redact_field_hash():
    """Test field redaction with hash strategy"""
    hashed = redact_field("nid", "sensitive", "hash", salt_ref="")
    assert len(hashed) == 16  # Truncated to 16 chars
    # Same input produces same hash
    assert redact_field("nid", "sensitive", "hash", salt_ref="") == hashed


@pytest.mark.gate_t
def test_redact_field_remove():
    """Test field redaction with remove strategy"""
    assert redact_field("name", "any-value", "remove") is None


@pytest.mark.gate_t
def test_redact_dict_recursive():
    """Test recursive dictionary redaction"""
    rules = {
        "email": {"strategy": "mask"},
        "phone": {"strategy": "mask"},
        "ssn": {"strategy": "remove"},
    }

    data = {
        "user": {
            "email": "test@example.com",
            "phone": "010-1234-5678",
            "ssn": "123-45-6789",
            "name": "John Doe",  # Not in rules, should remain
        },
        "meta": {
            "timestamp": "2025-01-01T00:00:00Z"
        }
    }

    redacted = redact_dict(data, rules)

    assert redacted["user"]["email"] == "t****@example.com"
    assert redacted["user"]["phone"] == "***-****-5678"
    assert redacted["user"]["ssn"] is None  # Removed
    assert redacted["user"]["name"] == "John Doe"  # Unchanged
    assert redacted["meta"]["timestamp"] == "2025-01-01T00:00:00Z"  # Unchanged


@pytest.mark.gate_t
def test_redact_evidence_with_config(tmp_path):
    """Test evidence redaction with config file"""
    # Create temp config
    config_path = tmp_path / "redact.yaml"
    config_path.write_text("""version: v1
fields:
  email: { strategy: mask }
  phone: { strategy: mask }
  name: { strategy: remove }
""")

    evidence = {
        "meta": {"tenant": "test"},
        "user_data": {
            "email": "user@example.com",
            "phone": "010-1234-5678",
            "name": "John Doe",
        }
    }

    redacted = redact_evidence(evidence, str(config_path))

    assert redacted["user_data"]["email"] == "u****@example.com"
    assert redacted["user_data"]["phone"] == "***-****-5678"
    assert redacted["user_data"]["name"] is None  # Removed
    assert redacted["meta"]["tenant"] == "test"  # Unchanged


@pytest.mark.gate_t
def test_redact_evidence_no_config():
    """Test evidence redaction without config returns original"""
    evidence = {"email": "test@example.com"}
    result = redact_evidence(evidence, "nonexistent.yaml")
    # Should return original if config not found
    assert result == evidence


@pytest.mark.gate_t
def test_redact_list_of_dicts():
    """Test redaction works with lists of dictionaries"""
    rules = {"email": {"strategy": "mask"}}

    data = {
        "users": [
            {"email": "user1@example.com", "id": 1},
            {"email": "user2@example.com", "id": 2},
        ]
    }

    redacted = redact_dict(data, rules)

    assert redacted["users"][0]["email"] == "u****@example.com"
    assert redacted["users"][0]["id"] == 1
    assert redacted["users"][1]["email"] == "u****@example.com"
    assert redacted["users"][1]["id"] == 2


@pytest.mark.gate_t
def test_redact_with_env_salt(monkeypatch, tmp_path):
    """Test hash strategy with salt from environment variable"""
    monkeypatch.setenv("DECISIONOS_HASH_SALT", "env-salt-value")

    config_path = tmp_path / "redact.yaml"
    config_path.write_text("""version: v1
fields:
  nid: { strategy: hash, salt_ref: "ENV:DECISIONOS_HASH_SALT" }
""")

    evidence = {"nid": "123456-1234567"}
    redacted = redact_evidence(evidence, str(config_path))

    # Should be hashed (truncated to 16 chars)
    assert len(redacted["nid"]) == 16
    assert redacted["nid"] != "123456-1234567"
