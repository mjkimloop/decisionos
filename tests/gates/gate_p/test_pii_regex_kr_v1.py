"""
Gate P — PII regex pattern detection tests (Korean context)
"""
import json
import os
import re
import pytest
from pathlib import Path

pytestmark = pytest.mark.gate_p


def _load_patterns():
    """Load PII patterns configuration"""
    path = Path("configs/pii/patterns_kr.json")
    return json.loads(path.read_text(encoding="utf-8"))


def test_detect_samples():
    """Test that patterns detect known PII samples"""
    cfg = _load_patterns()

    samples = {
        "resident_id": "900101-1234567",
        "mobile_phone": "010-1234-5678",
        "email": "a@b.co",
        "credit_card": "4111 1111 1111 1111"
    }

    for pii_type, value in samples.items():
        pat = re.compile(cfg[pii_type]["pattern"])
        assert pat.search(value), f"Pattern {pii_type} should match {value}"


def test_luhn_filter():
    """Test that Luhn validation filters fake credit cards"""
    os.environ["DECISIONOS_PII_TOKEN_KEY"] = "secret"

    from apps.security.pii.redactor import redact_text

    cfg = _load_patterns()

    # Valid card (passes Luhn) + fake card (fails Luhn)
    text = "카드 4111 1111 1111 1111 / 가짜카드 1234 1234 1234 1234"

    out = redact_text(text, cfg)

    # Valid card should be tokenized
    assert "TKN:credit_card" in out

    # Fake card should NOT be tokenized
    assert "1234 1234 1234 1234" in out


def test_resident_id_detection():
    """Test resident ID pattern detection"""
    cfg = _load_patterns()
    pat = re.compile(cfg["resident_id"]["pattern"])

    # With dash
    assert pat.search("900101-1234567")

    # Without dash
    assert pat.search("9001011234567")

    # Invalid format
    assert not pat.search("90010-1234567")


def test_mobile_phone_detection():
    """Test mobile phone pattern detection"""
    cfg = _load_patterns()
    pat = re.compile(cfg["mobile_phone"]["pattern"])

    valid_numbers = [
        "010-1234-5678",
        "011-123-4567",
        "016-1234-5678",
        "017-123-4567",
        "018-1234-5678",
        "019-123-4567"
    ]

    for num in valid_numbers:
        assert pat.search(num), f"Should match {num}"


def test_email_detection():
    """Test email pattern detection"""
    cfg = _load_patterns()
    pat = re.compile(cfg["email"]["pattern"])

    valid_emails = [
        "user@example.com",
        "test.user@sub.domain.co.kr",
        "name+tag@service.net"
    ]

    for email in valid_emails:
        assert pat.search(email), f"Should match {email}"


def test_bank_account_detection():
    """Test bank account pattern detection"""
    cfg = _load_patterns()
    pat = re.compile(cfg["bank_account"]["pattern"])

    valid_accounts = [
        "110-123-456789",
        "456-7890-123456",
        "1234-56789012-34"
    ]

    for acc in valid_accounts:
        assert pat.search(acc), f"Should match {acc}"
