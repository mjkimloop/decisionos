from apps.security.pii import redact_text


def test_mask_text_samples():
    s = "이메일 a.b@example.com / 전화 010-1234-5678 / 주민 900101-1234567"
    masked = redact_text(s)
    assert "a.b@example.com" not in masked
    assert "010-1234-5678" not in masked
    assert "900101-1234567" not in masked
