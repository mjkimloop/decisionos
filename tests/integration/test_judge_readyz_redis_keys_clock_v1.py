import json
import pytest
from apps.judge.keyloader_kms import load_from_ssm

pytestmark = pytest.mark.integration

def test_keyloader_env_fallback(monkeypatch):
    monkeypatch.setenv("DECISIONOS_KMS_SSM_PATH", "")
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", json.dumps([{"key_id": "k1", "secret": "s1", "state": "active"}]))
    data = load_from_ssm()
    # Without path configured, loader should fallback to env (empty list expected)
    assert data == []
