import json
import pytest
from apps.judge.crypto import MultiKeyLoader

pytestmark = [pytest.mark.gate_aj]


def test_multi_key_loader(monkeypatch):
    keys = [
        {"key_id": "k1", "secret": "hex:616161", "state": "active"},
        {"key_id": "k2", "secret": "hex:626262", "state": "grace"},
    ]
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", json.dumps(keys))
    loader = MultiKeyLoader()
    assert loader.get("k1").key_id == "k1"
    assert loader.choose_active().key_id == "k1"
