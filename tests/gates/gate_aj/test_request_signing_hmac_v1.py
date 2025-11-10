import pytest

pytestmark = [pytest.mark.gate_aj]

from apps.judge.crypto import hmac_sign_canonical, hmac_verify_canonical


def test_hmac_signing_is_deterministic():
    payload = {"metric": "latency", "value": 120, "tags": {"route": "rag"}}
    sig1 = hmac_sign_canonical(payload, "secret")
    sig2 = hmac_sign_canonical(payload, "secret")
    assert sig1 == sig2


def test_hmac_signing_detects_body_change():
    payload = {"metric": "latency", "value": 120}
    sig = hmac_sign_canonical(payload, "secret")
    tampered = {"metric": "latency", "value": 130}
    assert not hmac_verify_canonical(tampered, "secret", sig)


def test_hmac_signing_detects_key_change():
    payload = {"metric": "latency", "value": 120}
    sig = hmac_sign_canonical(payload, "secret")
    assert not hmac_verify_canonical(payload, "another", sig)
