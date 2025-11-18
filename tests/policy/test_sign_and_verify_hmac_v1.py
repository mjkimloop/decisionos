"""Tests for policy signing and verification (HMAC)."""
from __future__ import annotations

import base64
import json
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def test_keys():
    """Test HMAC keys configuration."""
    return json.dumps(
        [
            {
                "key_id": "test-k1",
                "secret": base64.b64encode(b"test-secret-1" * 2).decode("ascii"),
                "state": "active",
                "not_before": "2025-01-01T00:00:00Z",
                "not_after": "2026-01-01T00:00:00Z",
            },
            {
                "key_id": "test-k2",
                "secret": base64.b64encode(b"test-secret-2" * 2).decode("ascii"),
                "state": "grace",
                "not_before": "2025-11-01T00:00:00Z",
                "not_after": "2026-03-01T00:00:00Z",
            },
        ]
    )


@pytest.fixture
def test_policy_file(tmp_path):
    """Create temporary policy file."""
    policy = {"budget": {"max_spent": 1000}, "latency": {"max_p95_ms": 500}}
    policy_file = tmp_path / "test_policy.json"
    with open(policy_file, "w", encoding="utf-8") as f:
        json.dump(policy, f)
    return str(policy_file)


@pytest.mark.policy
def test_sign_policy_hmac(monkeypatch, test_keys, test_policy_file):
    """Test: Sign policy file with HMAC."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS_JSON", test_keys)

    from scripts.policy.sign import sign_file, write_signature

    # Sign file
    sig_data = sign_file(test_policy_file, key_id="test-k1", issuer="test")

    # Check signature metadata
    assert sig_data["version"] == 1
    assert sig_data["issuer"] == "test"
    assert sig_data["policy_file"] == "test_policy.json"
    assert sig_data["algorithm"] == "hmac-sha256"
    assert sig_data["key_id"] == "test-k1"
    assert "sha256" in sig_data
    assert "signature" in sig_data
    assert "created_at" in sig_data

    # Write signature
    sig_path = write_signature(test_policy_file, sig_data)
    assert os.path.exists(sig_path)
    assert sig_path == f"{test_policy_file}.sig"


@pytest.mark.policy
def test_verify_policy_hmac(monkeypatch, test_keys, test_policy_file):
    """Test: Verify signed policy file."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS_JSON", test_keys)

    from scripts.policy.sign import sign_file, write_signature
    from scripts.policy.verify import verify_file

    # Sign file
    sig_data = sign_file(test_policy_file, key_id="test-k1")
    write_signature(test_policy_file, sig_data)

    # Verify file
    passed, warnings = verify_file(test_policy_file, strict=True)

    assert passed is True
    assert len(warnings) == 0


@pytest.mark.policy
def test_verify_policy_unsigned(test_policy_file):
    """Test: Verification fails for unsigned policy."""
    from scripts.policy.verify import verify_file

    # Verify unsigned file (fail-closed)
    passed, warnings = verify_file(test_policy_file, strict=True, fail_open=False)

    assert passed is False
    assert any("No signature found" in w for w in warnings)


@pytest.mark.policy
def test_verify_policy_fail_open(test_policy_file):
    """Test: Fail-open mode allows unsigned files."""
    from scripts.policy.verify import verify_file

    # Verify unsigned file (fail-open)
    passed, warnings = verify_file(test_policy_file, strict=False, fail_open=True)

    assert passed is True
    assert any("allowed by fail-open" in w for w in warnings)


@pytest.mark.policy
def test_verify_policy_tampered(monkeypatch, test_keys, test_policy_file):
    """Test: Verification fails if policy is tampered."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS_JSON", test_keys)

    from scripts.policy.sign import sign_file, write_signature
    from scripts.policy.verify import verify_file

    # Sign file
    sig_data = sign_file(test_policy_file, key_id="test-k1")
    write_signature(test_policy_file, sig_data)

    # Tamper with policy
    with open(test_policy_file, "a", encoding="utf-8") as f:
        f.write("\n# tampered\n")

    # Verify file
    passed, warnings = verify_file(test_policy_file, strict=True)

    assert passed is False
    assert any("Hash mismatch" in w for w in warnings)


@pytest.mark.policy
def test_verify_policy_allowlist_pass(monkeypatch, test_keys, test_policy_file):
    """Test: Allowlist check passes for allowed key."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS_JSON", test_keys)
    monkeypatch.setenv("DECISIONOS_POLICY_ALLOWLIST", "test-k1,test-k2")

    from scripts.policy.sign import sign_file, write_signature
    from scripts.policy.verify import verify_file

    # Sign with allowed key
    sig_data = sign_file(test_policy_file, key_id="test-k1")
    write_signature(test_policy_file, sig_data)

    # Verify
    passed, warnings = verify_file(test_policy_file, strict=True)

    assert passed is True


@pytest.mark.policy
def test_verify_policy_allowlist_fail(monkeypatch, test_keys, test_policy_file):
    """Test: Allowlist check fails for disallowed key."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS_JSON", test_keys)
    monkeypatch.setenv("DECISIONOS_POLICY_ALLOWLIST", "test-k2")  # Only k2 allowed

    from scripts.policy.sign import sign_file, write_signature
    from scripts.policy.verify import verify_file

    # Sign with k1 (not in allowlist)
    sig_data = sign_file(test_policy_file, key_id="test-k1")
    write_signature(test_policy_file, sig_data)

    # Verify in strict mode
    passed, warnings = verify_file(test_policy_file, strict=True)

    assert passed is False
    assert any("not in allowlist" in w for w in warnings)


@pytest.mark.policy
def test_sign_with_grace_key(monkeypatch, test_keys, test_policy_file):
    """Test: Can sign with grace key."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS_JSON", test_keys)

    from scripts.policy.sign import sign_file

    # Sign with grace key (k2)
    sig_data = sign_file(test_policy_file, key_id="test-k2")

    assert sig_data["key_id"] == "test-k2"


@pytest.mark.policy
def test_verify_with_grace_key(monkeypatch, test_keys, test_policy_file):
    """Test: Can verify signature from grace key."""
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS_JSON", test_keys)

    from scripts.policy.sign import sign_file, write_signature
    from scripts.policy.verify import verify_file

    # Sign with grace key
    sig_data = sign_file(test_policy_file, key_id="test-k2")
    write_signature(test_policy_file, sig_data)

    # Verify
    passed, warnings = verify_file(test_policy_file, strict=True)

    assert passed is True
