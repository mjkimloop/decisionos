"""
Gate Sec — PII Redaction 테스트

이메일/전화번호/주민번호 등 개인정보 마스킹 검증
"""
import pytest

pytestmark = pytest.mark.gate_sec


def test_pii_redactor_init():
    """PII Redactor 초기화"""
    from apps.security.pii import PIIRedactor

    redactor = PIIRedactor()

    assert redactor.rules is not None
    assert len(redactor.rules) > 0


def test_redact_email():
    """이메일 마스킹"""
    from apps.security.pii import redact_string

    text = "Contact me at user@example.com for details"
    result = redact_string(text)

    assert "user@example.com" not in result
    assert "@" in result or "****" in result


def test_redact_phone_kr():
    """한국 전화번호 마스킹"""
    from apps.security.pii import redact_string

    text = "My phone is 010-1234-5678"
    result = redact_string(text)

    assert "010-1234-5678" not in result
    assert "***" in result or "****" in result


def test_redact_dict_email_field():
    """딕셔너리 이메일 필드 마스킹"""
    from apps.security.pii import redact_dict

    data = {
        "name": "홍길동",
        "email": "hong@example.com",
        "age": 30
    }

    result = redact_dict(data)

    assert result["age"] == 30
    assert "hong@example.com" not in str(result)


def test_redact_dict_recursive():
    """중첩 딕셔너리 재귀 마스킹"""
    from apps.security.pii import redact_dict

    data = {
        "user": {
            "name": "홍길동",
            "contact": {
                "email": "hong@example.com",
                "phone": "010-1234-5678"
            }
        }
    }

    result = redact_dict(data)

    assert "hong@example.com" not in str(result)
    assert "010-1234-5678" not in str(result)


def test_tokenize_value():
    """값 토큰화 (SHA256)"""
    from apps.security.pii import PIIRedactor, PIIRule

    redactor = PIIRedactor()

    rule = PIIRule(
        name="test",
        pattern=r"test",
        action="tokenize"
    )

    token = redactor._tokenize_value("sensitive@example.com", rule)

    assert token.startswith("tok_")
    assert len(token) > 4


def test_get_redactor_singleton():
    """싱글톤 Redactor 인스턴스"""
    from apps.security.pii import get_redactor

    r1 = get_redactor()
    r2 = get_redactor()

    assert r1 is r2


def test_redact_list_items():
    """리스트 항목 마스킹"""
    from apps.security.pii import redact_dict

    data = {
        "emails": [
            "user1@example.com",
            "user2@example.com"
        ]
    }

    result = redact_dict(data)

    assert isinstance(result["emails"], list)
    assert "user1@example.com" not in str(result)
