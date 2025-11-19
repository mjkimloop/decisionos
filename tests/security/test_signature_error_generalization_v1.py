# tests/security/test_signature_error_generalization_v1.py
"""
Security test: Signature verification error generalization (v0.5.11u-5).

Validates:
- External responses use generic "invalid signature" message
- Detailed failure reasons logged internally only
- No info leakage about keys, signatures, or verification process
"""
from __future__ import annotations

import pytest
from apps.judge.crypto import (
    MultiKeyLoader,
    SignatureInvalid,
    verify_signature_safe,
    verify_with_multikey,
)


def test_signature_invalid_exception_is_generic():
    """SignatureInvalid exception should have generic message."""
    exc = SignatureInvalid()
    assert str(exc) == "invalid signature"
    assert exc.reason == "invalid signature"


def test_verify_signature_safe_raises_generic_on_key_missing(monkeypatch):
    """Missing key should raise generic exception."""
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", "[]")

    loader = MultiKeyLoader()
    payload = {"foo": "bar"}
    signature = "deadbeef"
    key_id = "nonexistent"

    with pytest.raises(SignatureInvalid) as exc_info:
        verify_signature_safe(payload, signature, key_id, loader)

    # External message is generic
    assert str(exc_info.value) == "invalid signature"
    # Internal reason is NOT exposed
    assert "key.missing" not in str(exc_info.value)


def test_verify_signature_safe_raises_generic_on_sig_mismatch(monkeypatch):
    """Signature mismatch should raise generic exception."""
    monkeypatch.setenv(
        "DECISIONOS_JUDGE_KEYS", '[{"key_id":"k1","secret":"topsecret","state":"active"}]'
    )

    loader = MultiKeyLoader()
    payload = {"foo": "bar"}
    wrong_signature = "wrongsignature"
    key_id = "k1"

    with pytest.raises(SignatureInvalid) as exc_info:
        verify_signature_safe(payload, wrong_signature, key_id, loader)

    # External message is generic
    assert str(exc_info.value) == "invalid signature"
    # Internal reason is NOT exposed
    assert "sig.mismatch" not in str(exc_info.value)
    assert "topsecret" not in str(exc_info.value)


def test_verify_signature_safe_raises_generic_on_retired_key(monkeypatch):
    """Retired key should raise generic exception."""
    monkeypatch.setenv(
        "DECISIONOS_JUDGE_KEYS", '[{"key_id":"k1","secret":"topsecret","state":"retired"}]'
    )

    loader = MultiKeyLoader()
    payload = {"foo": "bar"}
    signature = "anysignature"
    key_id = "k1"

    with pytest.raises(SignatureInvalid) as exc_info:
        verify_signature_safe(payload, signature, key_id, loader)

    # External message is generic
    assert str(exc_info.value) == "invalid signature"
    # Internal reason is NOT exposed
    assert "retired" not in str(exc_info.value)


def test_verify_signature_safe_succeeds_silently(monkeypatch):
    """Valid signature should succeed without exception."""
    monkeypatch.setenv(
        "DECISIONOS_JUDGE_KEYS", '[{"key_id":"k1","secret":"topsecret","state":"active"}]'
    )

    loader = MultiKeyLoader()
    payload = {"foo": "bar"}

    # Compute correct signature
    from apps.judge.crypto import hmac_sign_canonical

    correct_signature = hmac_sign_canonical(payload, "topsecret")
    key_id = "k1"

    # Should not raise
    verify_signature_safe(payload, correct_signature, key_id, loader)


def test_internal_verify_still_returns_detailed_reason(monkeypatch):
    """Internal verify_with_multikey should still return detailed reasons."""
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", "[]")

    loader = MultiKeyLoader()
    payload = {"foo": "bar"}
    signature = "deadbeef"
    key_id = "nonexistent"

    ok, reason = verify_with_multikey(payload, signature, key_id, loader)

    # Internal function still provides detailed reason
    assert ok is False
    assert reason == "key.missing"


def test_grace_key_allowed_internally_but_generic_externally(monkeypatch):
    """Grace key should work internally but not leak state externally."""
    monkeypatch.setenv(
        "DECISIONOS_JUDGE_KEYS", '[{"key_id":"k1","secret":"topsecret","state":"grace"}]'
    )

    loader = MultiKeyLoader()
    payload = {"foo": "bar"}

    from apps.judge.crypto import hmac_sign_canonical

    correct_signature = hmac_sign_canonical(payload, "topsecret")
    key_id = "k1"

    # Should succeed (grace key allowed by default)
    verify_signature_safe(payload, correct_signature, key_id, loader, allow_grace=True)

    # If grace forbidden, should raise generic exception
    with pytest.raises(SignatureInvalid) as exc_info:
        verify_signature_safe(payload, correct_signature, key_id, loader, allow_grace=False)

    # Generic message
    assert str(exc_info.value) == "invalid signature"
    # State not leaked
    assert "grace" not in str(exc_info.value)


def test_judge_server_returns_generic_401(monkeypatch):
    """Judge server should return generic 401 for bad signature."""
    monkeypatch.setenv("DECISIONOS_ENV", "dev")
    monkeypatch.setenv(
        "DECISIONOS_JUDGE_KEYS", '[{"key_id":"k1","secret":"topsecret","state":"active"}]'
    )

    from apps.judge.server import create_app
    from starlette.testclient import TestClient

    app = create_app()
    client = TestClient(app)

    # Bad signature
    r = client.post(
        "/judge",
        json={"evidence": {}, "slo": {}},
        headers={
            "X-Key-Id": "k1",
            "X-DecisionOS-Signature": "badsignature",
            "X-DecisionOS-Nonce": "test-nonce",
            "X-DecisionOS-Timestamp": "1700000000",
        },
    )

    assert r.status_code == 401
    # Generic error message
    assert r.json()["detail"] == "invalid signature"
    # No detailed reason leaked
    assert "sig.mismatch" not in r.json()["detail"]
    assert "key" not in r.json()["detail"]
