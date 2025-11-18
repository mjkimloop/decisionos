import pytest
from apps.security.pii import redact_text

pytestmark = pytest.mark.gate_t

def test_pii_redacts_email_and_phone():
    text = "Contact test@example.com or 010-1234-5678"
    redacted = redact_text(text)
    assert "test@example.com" not in redacted
    assert "010-1234-5678" not in redacted
