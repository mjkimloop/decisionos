import json
import pytest
from apps.judge.crypto import MultiKeyLoader, hmac_sign, verify_with_multikey

pytestmark = [pytest.mark.gate_aj]


def test_grace_key_verifies_but_not_active(monkeypatch):
    keys = [{"key_id": "k1", "secret": "abcd", "state": "grace"}]
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", json.dumps(keys))
    loader = MultiKeyLoader()
    payload = {"x": 1}
    sig = hmac_sign(payload, b"abcd")
    ok, reason = verify_with_multikey(payload, sig, "k1", loader)
    assert ok and reason == "ok"
    # active 선택은 None
    assert loader.choose_active() is None
