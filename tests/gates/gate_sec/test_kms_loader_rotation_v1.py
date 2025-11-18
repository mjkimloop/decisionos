"""
Gate SEC — KMS Loader rotation with ENV > SSM priority, grace period, audit logging
"""
import os
import time
import json
import tempfile
from apps.secrets.kms_loader import KMSLoader, build_kms_loader

def test_load_key_from_env():
    """Test loading key from ENV"""
    os.environ["DECISIONOS_KEY_JUDGE_HMAC"] = "test-key-env-123"
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"keys": {"judge-hmac": {"role": "test", "grace_window_sec": 1}}}, f)
        policy_path = f.name
    
    try:
        loader = KMSLoader(policy_path)
        kv = loader.load_key("judge-hmac")
        
        assert kv is not None
        assert kv.key_id == "judge-hmac"
        assert kv.value == "test-key-env-123"
        assert kv.source == "ENV"
        assert kv.version == "env"
        assert len(kv.hash_prefix) == 8
    finally:
        os.unlink(policy_path)
        del os.environ["DECISIONOS_KEY_JUDGE_HMAC"]

def test_env_priority_over_ssm():
    """Test ENV takes priority over SSM"""
    os.environ["DECISIONOS_KEY_JUDGE_HMAC"] = "env-key"
    os.environ["SSM_JUDGE_HMAC"] = "ssm-key"
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"keys": {"judge-hmac": {"role": "test", "grace_window_sec": 1}}}, f)
        policy_path = f.name
    
    try:
        loader = KMSLoader(policy_path)
        kv = loader.load_key("judge-hmac")
        
        assert kv.value == "env-key"
        assert kv.source == "ENV"
    finally:
        os.unlink(policy_path)
        del os.environ["DECISIONOS_KEY_JUDGE_HMAC"]
        del os.environ["SSM_JUDGE_HMAC"]

def test_fallback_to_ssm():
    """Test fallback to SSM when ENV not set"""
    os.environ["SSM_JUDGE_HMAC"] = "ssm-key-only"
    os.environ["DECISIONOS_SSM_PARAM_KEYS"] = "/test/keys"
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"keys": {"judge-hmac": {"role": "test", "grace_window_sec": 1}}}, f)
        policy_path = f.name
    
    try:
        loader = KMSLoader(policy_path)
        kv = loader.load_key("judge-hmac")
        
        assert kv.value == "ssm-key-only"
        assert kv.source == "SSM"
    finally:
        os.unlink(policy_path)
        del os.environ["SSM_JUDGE_HMAC"]
        del os.environ["DECISIONOS_SSM_PARAM_KEYS"]

def test_grace_period_allows_old_key():
    """Test grace period allows old key during rotation"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"keys": {"judge-hmac": {"role": "test", "grace_window_sec": 2}}}, f)
        policy_path = f.name
    
    try:
        loader = KMSLoader(policy_path)
        
        # Load initial key
        os.environ["DECISIONOS_KEY_JUDGE_HMAC"] = "old-key-v1"
        loader.load_key("judge-hmac")
        assert loader.get_key("judge-hmac") == "old-key-v1"
        
        # Rotate key
        os.environ["DECISIONOS_KEY_JUDGE_HMAC"] = "new-key-v2"
        loader.load_key("judge-hmac")
        
        # New key should be active
        assert loader.get_key("judge-hmac") == "new-key-v2"
        
        # Old key should still be in grace period
        assert "judge-hmac" in loader._grace_keys
        
        # After grace expires, old key should be gone
        time.sleep(2.1)
        stale = loader.check_stale_versions()
        assert len(stale) == 0  # Grace expired
        
    finally:
        os.unlink(policy_path)
        if "DECISIONOS_KEY_JUDGE_HMAC" in os.environ:
            del os.environ["DECISIONOS_KEY_JUDGE_HMAC"]

def test_stale_version_warning():
    """Test stale version detection during grace period"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"keys": {"judge-hmac": {"role": "test", "grace_window_sec": 5}}}, f)
        policy_path = f.name
    
    try:
        loader = KMSLoader(policy_path)
        
        # Load initial key
        os.environ["DECISIONOS_KEY_JUDGE_HMAC"] = "v1"
        loader.load_key("judge-hmac")
        
        # Rotate
        os.environ["DECISIONOS_KEY_JUDGE_HMAC"] = "v2"
        loader.load_key("judge-hmac")
        
        # Check stale versions (should have 1 in grace)
        stale = loader.check_stale_versions()
        assert len(stale) == 1
        assert "judge-hmac" in stale[0]
        
    finally:
        os.unlink(policy_path)
        del os.environ["DECISIONOS_KEY_JUDGE_HMAC"]

def test_audit_log_records_loads():
    """Test audit log records key_id, version, source, loaded_at"""
    os.environ["DECISIONOS_KEY_JUDGE_HMAC"] = "audit-test-key"
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"keys": {"judge-hmac": {"role": "test", "grace_window_sec": 1}}}, f)
        policy_path = f.name
    
    try:
        loader = KMSLoader(policy_path)
        loader.load_key("judge-hmac")
        
        log = loader.get_audit_log()
        assert len(log) == 1
        
        entry = log[0]
        assert entry["key_id"] == "judge-hmac"
        assert entry["version"] == "env"
        assert entry["source"] == "ENV"
        assert "loaded_at" in entry
        assert "hash_prefix" in entry
        assert len(entry["hash_prefix"]) == 8
        
    finally:
        os.unlink(policy_path)
        del os.environ["DECISIONOS_KEY_JUDGE_HMAC"]

def test_degraded_state_on_missing_key():
    """Test degraded state when key fails to load"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"keys": {"missing-key": {"role": "test", "grace_window_sec": 1}}}, f)
        policy_path = f.name
    
    try:
        loader = KMSLoader(policy_path)
        success = loader.load_all_keys()
        
        assert not success
        assert loader._degraded
        assert not loader.is_ready()
        
    finally:
        os.unlink(policy_path)

def test_is_ready_green_after_successful_load():
    """Test is_ready() returns True after successful load"""
    os.environ["DECISIONOS_KEY_JUDGE_HMAC"] = "ready-key"
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"keys": {"judge-hmac": {"role": "test", "grace_window_sec": 1}}}, f)
        policy_path = f.name
    
    try:
        loader = build_kms_loader(policy_path)
        assert loader.is_ready()
        
    finally:
        os.unlink(policy_path)
        del os.environ["DECISIONOS_KEY_JUDGE_HMAC"]

def test_allowed_sources_restriction():
    """Test allowed_sources policy restricts loading"""
    os.environ["DECISIONOS_KEY_RESTRICTED"] = "env-val"
    os.environ["SSM_RESTRICTED"] = "ssm-val"
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        # Only allow SSM for this key
        json.dump({"keys": {"restricted": {"role": "test", "allowed_sources": ["SSM"], "grace_window_sec": 1}}}, f)
        policy_path = f.name
    
    try:
        os.environ["DECISIONOS_SSM_PARAM_KEYS"] = "/test/keys"
        loader = KMSLoader(policy_path)
        kv = loader.load_key("restricted")
        
        # Should load from SSM only, not ENV
        assert kv is not None
        assert kv.source == "SSM"
        assert kv.value == "ssm-val"
        
    finally:
        os.unlink(policy_path)
        del os.environ["DECISIONOS_KEY_RESTRICTED"]
        del os.environ["SSM_RESTRICTED"]
        del os.environ["DECISIONOS_SSM_PARAM_KEYS"]
