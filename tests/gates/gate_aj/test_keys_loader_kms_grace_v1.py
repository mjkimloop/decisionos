import json

import pytest

from apps.judge.crypto import MultiKeyLoader, hmac_sign, verify_with_multikey

pytestmark = [pytest.mark.gate_aj]


def test_multikey_states_and_grace(monkeypatch):
    payload = {"decision": "pass"}
    keys = [
        {"key_id": "active", "secret": "hex:0f0f", "state": "active"},
        {"key_id": "grace", "secret": "hex:1111", "state": "grace"},
        {"key_id": "retired", "secret": "hex:2222", "state": "retired"},
    ]
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", json.dumps(keys))
    loader = MultiKeyLoader()

    active_sig = hmac_sign(payload, bytes.fromhex("0f0f"))
    ok, reason = verify_with_multikey(payload, active_sig, "active", loader)
    assert ok and reason == "ok"

    grace_sig = hmac_sign(payload, bytes.fromhex("1111"))
    ok, reason = verify_with_multikey(payload, grace_sig, "grace", loader)
    assert ok and reason == "key.grace"
    ok, reason = verify_with_multikey(payload, grace_sig, "grace", loader, allow_grace=False)
    assert not ok and reason == "key.grace_forbidden"

    retired_sig = hmac_sign(payload, bytes.fromhex("2222"))
    ok, reason = verify_with_multikey(payload, retired_sig, "retired", loader)
    assert not ok and reason == "key.retired"

    info = loader.info()
    assert info["states"]["active"] == 1
    assert info["states"]["grace"] == 1
    assert info["states"]["retired"] == 1
