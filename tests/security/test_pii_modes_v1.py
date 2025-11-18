"""Tests for PII soft/hard mode redaction."""
from __future__ import annotations

import pytest


@pytest.mark.security
def test_pii_soft_mode_email(monkeypatch):
    """Test: Soft mode partially masks email."""
    monkeypatch.setenv("DECISIONOS_PII_MODE", "soft")

    from apps.security.pii_rules import mask_text_with_count

    text = "Contact: john.doe@example.com"
    masked, count = mask_text_with_count(text)

    assert count == 1
    assert "REDACTED" not in masked
    assert "@example.com" in masked  # Domain preserved
    assert "john" in masked or "j" in masked  # First char preserved


@pytest.mark.security
def test_pii_hard_mode_email(monkeypatch):
    """Test: Hard mode fully redacts email."""
    monkeypatch.setenv("DECISIONOS_PII_MODE", "hard")

    from apps.security.pii_rules import mask_text_with_count

    text = "Contact: john.doe@example.com"
    masked, count = mask_text_with_count(text)

    assert count == 1
    assert "[REDACTED_EMAIL]" in masked
    assert "@example.com" not in masked


@pytest.mark.security
def test_pii_soft_mode_phone(monkeypatch):
    """Test: Soft mode partially masks phone."""
    monkeypatch.setenv("DECISIONOS_PII_MODE", "soft")

    from apps.security.pii_rules import mask_text_with_count

    text = "Call: 010-1234-5678"
    masked, count = mask_text_with_count(text)

    assert count == 1
    assert "***" in masked
    assert "010" in masked  # Prefix preserved
    assert "5678" in masked  # Last 4 digits preserved


@pytest.mark.security
def test_pii_hard_mode_phone(monkeypatch):
    """Test: Hard mode fully redacts phone."""
    monkeypatch.setenv("DECISIONOS_PII_MODE", "hard")

    from apps.security.pii_rules import mask_text_with_count

    text = "Call: 010-1234-5678"
    masked, count = mask_text_with_count(text)

    assert count == 1
    assert "[REDACTED_PHONE]" in masked
    assert "010" not in masked


@pytest.mark.security
def test_pii_soft_mode_rrn(monkeypatch):
    """Test: Soft mode partially masks RRN."""
    monkeypatch.setenv("DECISIONOS_PII_MODE", "soft")

    from apps.security.pii_rules import mask_text_with_count

    text = "RRN: 900101-1234567"
    masked, count = mask_text_with_count(text)

    assert count == 1
    assert "900101" in masked  # Birth date preserved
    assert "1" in masked  # Gender digit preserved
    assert "******" in masked  # Rest masked


@pytest.mark.security
def test_pii_hard_mode_rrn(monkeypatch):
    """Test: Hard mode fully redacts RRN."""
    monkeypatch.setenv("DECISIONOS_PII_MODE", "hard")

    from apps.security.pii_rules import mask_text_with_count

    text = "RRN: 900101-1234567"
    masked, count = mask_text_with_count(text)

    assert count == 1
    assert "[REDACTED_RRN]" in masked
    assert "900101" not in masked


@pytest.mark.security
def test_pii_soft_mode_card(monkeypatch):
    """Test: Soft mode partially masks card number."""
    monkeypatch.setenv("DECISIONOS_PII_MODE", "soft")

    from apps.security.pii_rules import mask_text_with_count

    text = "Card: 4111-2222-3333-4444"
    masked, count = mask_text_with_count(text)

    assert count == 1
    assert "4111" in masked  # First 4 preserved
    assert "4444" in masked  # Last 4 preserved
    assert "****" in masked  # Middle masked


@pytest.mark.security
def test_pii_hard_mode_card(monkeypatch):
    """Test: Hard mode fully redacts card number."""
    monkeypatch.setenv("DECISIONOS_PII_MODE", "hard")

    from apps.security.pii_rules import mask_text_with_count

    text = "Card: 4111-2222-3333-4444"
    masked, count = mask_text_with_count(text)

    assert count == 1
    assert "[REDACTED_CARD]" in masked
    assert "4111" not in masked


@pytest.mark.security
def test_pii_multiple_patterns(monkeypatch):
    """Test: Multiple PII patterns in one text."""
    monkeypatch.setenv("DECISIONOS_PII_MODE", "soft")

    from apps.security.pii_rules import mask_text_with_count

    text = "Email: a.b@example.com, Phone: 010-1234-5678, RRN: 900101-1234567, Card: 4111-2222-3333-4444, 서울강남로123"
    masked, count = mask_text_with_count(text)

    # Should detect all patterns
    assert count >= 4  # At least email, phone, RRN, card


@pytest.mark.security
def test_pii_obj_masking(monkeypatch):
    """Test: Recursive object masking."""
    monkeypatch.setenv("DECISIONOS_PII_MODE", "soft")

    from apps.security.pii_rules import mask_obj_with_stats

    obj = {
        "user": {
            "email": "test@example.com",
            "contacts": ["010-1111-2222", "010-3333-4444"],
        },
        "notes": "Call 010-5555-6666",
    }

    masked, count = mask_obj_with_stats(obj)

    assert count >= 4  # 1 email + 3 phones
    assert isinstance(masked, dict)
    assert "REDACTED" not in str(masked)  # Soft mode
