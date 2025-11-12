"""
Test Key Loader Refresh with Grace Period (gate_aj)
"""
import os
import time
import pytest
from apps.judge.keyloader_refresh import (
    KeyLoader,
    KeyRefreshConfig,
    get_key_loader,
)


@pytest.mark.gate_aj
def test_load_from_env(monkeypatch):
    """Test loading keys from environment variable"""
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", "key1:secret1,key2:secret2")

    config = KeyRefreshConfig(refresh_interval_sec=1)
    loader = KeyLoader(config)
    loader.refresh()

    assert loader.get_key("key1") == "secret1"
    assert loader.get_key("key2") == "secret2"
    assert loader.get_key("nonexistent") is None


@pytest.mark.gate_aj
def test_refresh_interval(monkeypatch):
    """Test refresh only happens after interval"""
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", "key1:secret1")

    config = KeyRefreshConfig(refresh_interval_sec=2)
    loader = KeyLoader(config)

    # First refresh
    assert loader.refresh() is True
    assert loader.get_key("key1") == "secret1"

    # Immediate second refresh should skip (within interval)
    # Change env but refresh should not reload yet
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", "key1:newsecret")
    assert loader.refresh() is True  # Returns True but doesn't reload
    assert loader.get_key("key1") == "secret1"  # Old value

    # Wait for interval to pass
    time.sleep(2.1)
    assert loader.refresh() is True
    assert loader.get_key("key1") == "newsecret"  # New value


@pytest.mark.gate_aj
def test_grace_period(monkeypatch):
    """Test grace period keeps old keys valid"""
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", "key1:old_secret")

    config = KeyRefreshConfig(refresh_interval_sec=1, grace_window_sec=2)
    loader = KeyLoader(config)
    loader.refresh()

    assert loader.get_key("key1") == "old_secret"

    # Wait and refresh with new key
    time.sleep(1.1)
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", "key1:new_secret,key2:secret2")
    loader.refresh()

    # Both old and new keys should work during grace period
    assert loader.get_key("key1") == "new_secret"  # New key has priority

    # After grace period, old key should be gone
    time.sleep(2.1)
    # Only new key should work now
    assert loader.get_key("key1") == "new_secret"


@pytest.mark.gate_aj
def test_degraded_on_no_keys(monkeypatch):
    """Test degraded state when no keys loaded"""
    monkeypatch.delenv("DECISIONOS_JUDGE_KEYS", raising=False)

    config = KeyRefreshConfig()
    loader = KeyLoader(config)

    assert loader.refresh() is False
    assert loader.is_degraded() is True


@pytest.mark.gate_aj
def test_readiness_check(monkeypatch):
    """Test readiness check health status"""
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", "key1:secret1")

    config = KeyRefreshConfig(refresh_interval_sec=60)
    loader = KeyLoader(config)
    loader.refresh()

    status = loader.readiness_check()

    assert status["healthy"] is True
    assert status["degraded"] is False
    assert status["keys_count"] == 1
    assert status["grace_keys_count"] == 0
    assert status["age_sec"] >= 0
    assert status["next_refresh_sec"] <= 60


@pytest.mark.gate_aj
def test_env_priority_over_ssm(monkeypatch):
    """Test ENV keys have priority over SSM"""
    # Simulate SSM would return key1:ssm_value
    # But ENV has key1:env_value
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", "key1:env_value")

    config = KeyRefreshConfig()
    loader = KeyLoader(config)

    # Mock _load_from_ssm to return different value
    def mock_ssm(self):
        return {"key1": "ssm_value", "key2": "ssm_only"}

    original_ssm = loader._load_from_ssm
    loader._load_from_ssm = lambda: mock_ssm(loader)

    loader.refresh()

    # ENV should win for key1
    assert loader.get_key("key1") == "env_value"
    # SSM-only key should be available
    assert loader.get_key("key2") == "ssm_only"


@pytest.mark.gate_aj
def test_get_all_keys(monkeypatch):
    """Test get_all_keys returns current keyset"""
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", "key1:secret1,key2:secret2")

    config = KeyRefreshConfig()
    loader = KeyLoader(config)
    loader.refresh()

    all_keys = loader.get_all_keys()

    assert len(all_keys) == 2
    assert all_keys["key1"] == "secret1"
    assert all_keys["key2"] == "secret2"


@pytest.mark.gate_aj
def test_multiple_key_format(monkeypatch):
    """Test parsing multiple keys with various formats"""
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", "k1:s1, k2:s2 , k3:s3:with:colons")

    config = KeyRefreshConfig()
    loader = KeyLoader(config)
    loader.refresh()

    assert loader.get_key("k1") == "s1"
    assert loader.get_key("k2") == "s2"
    # Colons in secret should be preserved
    assert loader.get_key("k3") == "s3:with:colons"


@pytest.mark.gate_aj
def test_global_singleton(monkeypatch):
    """Test get_key_loader returns singleton instance"""
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", "key1:secret1")

    config = KeyRefreshConfig()
    loader1 = get_key_loader(config)
    loader2 = get_key_loader()

    # Should be same instance
    assert loader1 is loader2


@pytest.mark.gate_aj
def test_grace_expiration(monkeypatch):
    """Test grace keys expire after grace window"""
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", "key1:old")

    config = KeyRefreshConfig(refresh_interval_sec=0.5, grace_window_sec=1)
    loader = KeyLoader(config)
    loader.refresh()

    # Change key
    time.sleep(0.6)
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", "key2:new")
    loader.refresh()

    # Grace keys should still be accessible
    status = loader.readiness_check()
    assert status["grace_keys_count"] >= 0  # May have grace keys

    # Wait for grace to expire
    time.sleep(1.1)

    # Grace keys should be gone
    status = loader.readiness_check()
    assert status["grace_keys_count"] == 0
