"""
Gate P — PII redactor tokenization tests
"""
import os
import json
import pytest
from pathlib import Path

pytestmark = pytest.mark.gate_p


def test_tokenization():
    """Test basic tokenization"""
    os.environ["DECISIONOS_PII_TOKEN_KEY"] = "secret"

    from apps.security.pii.redactor import redact_text

    cfg = json.loads(Path("configs/pii/patterns_kr.json").read_text(encoding="utf-8"))

    text = "연락처 010-1234-5678"
    out = redact_text(text, cfg)

    assert "TKN:mobile_phone:" in out
    assert "010-1234-5678" not in out


def test_tokenization_deterministic():
    """Test that same value produces same token"""
    os.environ["DECISIONOS_PII_TOKEN_KEY"] = "secret"

    from apps.security.pii.redactor import redact_text

    cfg = json.loads(Path("configs/pii/patterns_kr.json").read_text(encoding="utf-8"))

    text = "전화 010-1234-5678 그리고 010-1234-5678"
    out = redact_text(text, cfg)

    # Should have exactly 2 occurrences of the same token
    tokens = [t for t in out.split() if t.startswith("TKN:mobile_phone:")]
    assert len(tokens) == 2
    assert tokens[0] == tokens[1]


def test_multiple_pii_types():
    """Test redacting multiple PII types in one text"""
    os.environ["DECISIONOS_PII_TOKEN_KEY"] = "secret"

    from apps.security.pii.redactor import redact_text

    cfg = json.loads(Path("configs/pii/patterns_kr.json").read_text(encoding="utf-8"))

    text = "연락처 010-1234-5678, 이메일 user@example.com, 주민번호 900101-1234567"
    out = redact_text(text, cfg)

    assert "TKN:mobile_phone:" in out
    assert "TKN:email:" in out
    assert "TKN:resident_id:" in out

    # Original values should not appear
    assert "010-1234-5678" not in out
    assert "user@example.com" not in out
    assert "900101-1234567" not in out


def test_mask_mode():
    """Test mask mode instead of tokenization"""
    os.environ["DECISIONOS_PII_TOKEN_KEY"] = "secret"

    from apps.security.pii.redactor import redact_text

    cfg = json.loads(Path("configs/pii/patterns_kr.json").read_text(encoding="utf-8"))

    text = "전화 010-1234-5678"
    out = redact_text(text, cfg, mode="mask")

    assert "[REDACTED:mobile_phone]" in out
    assert "TKN:" not in out


def test_token_format():
    """Test token format is correct"""
    os.environ["DECISIONOS_PII_TOKEN_KEY"] = "secret"

    from apps.security.pii.tokenizer import token_of

    token = token_of("010-1234-5678", "mobile_phone")

    assert token.startswith("TKN:mobile_phone:")
    parts = token.split(":")
    assert len(parts) == 3
    assert len(parts[2]) == 8  # Hash should be 8 characters


def test_tokenization_requires_key():
    """Test that tokenization requires DECISIONOS_PII_TOKEN_KEY"""
    # Clear key
    if "DECISIONOS_PII_TOKEN_KEY" in os.environ:
        del os.environ["DECISIONOS_PII_TOKEN_KEY"]

    from apps.security.pii.tokenizer import token_of

    with pytest.raises(ValueError, match="DECISIONOS_PII_TOKEN_KEY"):
        token_of("test", "test_type")
