"""Tests for PolicyLoader fail-closed enforcement."""
from __future__ import annotations

import base64
import json
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def test_keys():
    """Test HMAC keys."""
    return json.dumps(
        [
            {
                "key_id": "loader-k1",
                "secret": base64.b64encode(b"loader-secret-1" * 2).decode("ascii"),
                "state": "active",
            }
        ]
    )


@pytest.fixture
def signed_policy(tmp_path, monkeypatch, test_keys):
    """Create signed policy file."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", test_keys)

    policy = {"budget": {"max_spent": 1000}}
    policy_file = tmp_path / "test.json"

    with open(policy_file, "w", encoding="utf-8") as f:
        json.dump(policy, f)

    # Create signature using judge.crypto
    from apps.judge.crypto import MultiKeyLoader, hmac_sign_canonical

    loader = MultiKeyLoader(env_var="DECISIONOS_POLICY_KEYS")
    loader.force_reload()
    material = loader.get("loader-k1")

    sig_data = {
        "version": 1,
        "key_id": "loader-k1",
        "hmac_sha256": hmac_sign_canonical(policy, material.secret),
    }

    sig_file = Path(f"{policy_file}.sig")
    with open(sig_file, "w", encoding="utf-8") as f:
        json.dump(sig_data, f)

    return str(policy_file)


@pytest.mark.policy
def test_loader_signed_policy_success(monkeypatch, test_keys, signed_policy):
    """Test: Loader accepts signed policy (fail-closed)."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", test_keys)
    monkeypatch.setenv("DECISIONOS_POLICY_FAIL_OPEN", "0")

    from apps.common.policy_loader import PolicyLoader

    loader = PolicyLoader()
    policy = loader.load(signed_policy)

    assert policy["budget"]["max_spent"] == 1000


@pytest.mark.policy
def test_loader_unsigned_policy_fail_closed(tmp_path, monkeypatch, test_keys):
    """Test: Loader rejects unsigned policy (fail-closed)."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", test_keys)
    monkeypatch.setenv("DECISIONOS_POLICY_FAIL_OPEN", "0")

    # Create unsigned policy
    policy_file = tmp_path / "unsigned.json"
    with open(policy_file, "w", encoding="utf-8") as f:
        json.dump({"test": "policy"}, f)

    from apps.common.policy_loader import PolicyLoader, PolicySignatureError

    loader = PolicyLoader()

    with pytest.raises(PolicySignatureError, match="signature missing"):
        loader.load(str(policy_file))


@pytest.mark.policy
def test_loader_unsigned_policy_fail_open(tmp_path, monkeypatch, test_keys):
    """Test: Loader allows unsigned policy (fail-open)."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", test_keys)
    monkeypatch.setenv("DECISIONOS_POLICY_FAIL_OPEN", "1")

    # Create unsigned policy
    policy_file = tmp_path / "unsigned.json"
    with open(policy_file, "w", encoding="utf-8") as f:
        json.dump({"test": "policy"}, f)

    from apps.common.policy_loader import PolicyLoader

    loader = PolicyLoader()
    policy = loader.load(str(policy_file))

    assert policy["test"] == "policy"


@pytest.mark.policy
def test_loader_tampered_policy_rejected(monkeypatch, test_keys, signed_policy):
    """Test: Loader rejects tampered policy."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", test_keys)

    from apps.common.policy_loader import PolicyLoader, PolicySignatureError

    # Tamper with policy (change content, keep valid JSON)
    with open(signed_policy, "w", encoding="utf-8") as f:
        json.dump({"budget": {"max_spent": 9999}}, f)  # Changed value

    loader = PolicyLoader()

    with pytest.raises(PolicySignatureError, match="signature mismatch"):
        loader.load(signed_policy)


@pytest.mark.policy
def test_loader_allowlist_pass(monkeypatch, test_keys, signed_policy):
    """Test: Loader accepts policy with allowed key."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", test_keys)
    monkeypatch.setenv("DECISIONOS_POLICY_ALLOWLIST", "loader-k1")

    from apps.common.policy_loader import PolicyLoader

    loader = PolicyLoader()
    policy = loader.load(signed_policy)

    assert policy["budget"]["max_spent"] == 1000


@pytest.mark.policy
def test_loader_allowlist_fail(monkeypatch, test_keys, signed_policy):
    """Test: Loader rejects policy with disallowed key."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", test_keys)
    monkeypatch.setenv("DECISIONOS_POLICY_ALLOWLIST", "other-key")  # loader-k1 not allowed

    from apps.common.policy_loader import PolicyLoader, PolicySignatureError

    loader = PolicyLoader()

    with pytest.raises(PolicySignatureError, match="not in allowlist"):
        loader.load(signed_policy)


@pytest.mark.policy
def test_loader_scope_restriction_pass(monkeypatch, test_keys, signed_policy):
    """Test: Loader allows access to allowed scope."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", test_keys)
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "slo,rbac,canary")

    from apps.common.policy_loader import PolicyLoader

    loader = PolicyLoader()
    policy = loader.load(signed_policy, scope="slo")

    assert policy["budget"]["max_spent"] == 1000


@pytest.mark.policy
def test_loader_scope_restriction_fail(monkeypatch, test_keys, signed_policy):
    """Test: Loader rejects access to disallowed scope."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", test_keys)
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "rbac,canary")  # slo not allowed

    from apps.common.policy_loader import PolicyLoader, PolicySignatureError

    loader = PolicyLoader()

    with pytest.raises(PolicySignatureError, match="not in DECISIONOS_ALLOW_SCOPES"):
        loader.load(signed_policy, scope="slo")


@pytest.mark.policy
def test_loader_scope_no_restriction(monkeypatch, test_keys, signed_policy):
    """Test: Loader allows all scopes when ALLOW_SCOPES not set."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", test_keys)
    # No DECISIONOS_ALLOW_SCOPES set

    from apps.common.policy_loader import PolicyLoader

    loader = PolicyLoader()
    policy = loader.load(signed_policy, scope="any-scope")

    assert policy["budget"]["max_spent"] == 1000
