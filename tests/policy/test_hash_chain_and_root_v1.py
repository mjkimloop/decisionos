"""Tests for policy registry and hash chain."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_policy_dir(tmp_path):
    """Create temporary policy directory with test policies."""
    policy_dir = tmp_path / "configs" / "policy"
    policy_dir.mkdir(parents=True)

    # Create test policy files
    policies = {
        "slo.json": {"budget": {"max_spent": 1000}},
        "rbac.json": {"roles": ["admin", "user"]},
        "canary.json": {"percent": 10},
    }

    for filename, content in policies.items():
        policy_file = policy_dir / filename
        with open(policy_file, "w", encoding="utf-8") as f:
            json.dump(content, f)

    return str(policy_dir)


@pytest.mark.policy
def test_registry_scan_policies(temp_policy_dir, monkeypatch):
    """Test: Registry scans policy directory."""
    monkeypatch.chdir(Path(temp_policy_dir).parent.parent)

    from scripts.policy.registry import scan_policies

    entries = scan_policies(temp_policy_dir)

    assert len(entries) == 3
    assert any(e["file"] == "slo.json" for e in entries)
    assert any(e["file"] == "rbac.json" for e in entries)
    assert any(e["file"] == "canary.json" for e in entries)

    # Check all entries have sha256
    for entry in entries:
        assert "sha256" in entry
        assert len(entry["sha256"]) == 64  # SHA256 hex length


@pytest.mark.policy
def test_registry_compute_root_hash(temp_policy_dir, monkeypatch):
    """Test: Registry computes deterministic root hash."""
    monkeypatch.chdir(Path(temp_policy_dir).parent.parent)

    from scripts.policy.registry import _compute_root_hash, scan_policies

    entries = scan_policies(temp_policy_dir)
    root_hash_1 = _compute_root_hash(entries)
    root_hash_2 = _compute_root_hash(entries)

    # Root hash should be deterministic
    assert root_hash_1 == root_hash_2
    assert len(root_hash_1) == 64  # SHA256 hex length


@pytest.mark.policy
def test_registry_update(temp_policy_dir, monkeypatch):
    """Test: Registry update creates registry.json."""
    monkeypatch.chdir(Path(temp_policy_dir).parent.parent)

    from scripts.policy.registry import REGISTRY_PATH, save_registry, update_registry

    registry = update_registry(temp_policy_dir)

    # Check registry structure
    assert registry["version"] == 1
    assert "root_hash" in registry
    assert "entries" in registry
    assert "chain" in registry

    # Check entries
    assert len(registry["entries"]) == 3

    # Check chain
    assert len(registry["chain"]) >= 1
    assert registry["chain"][-1]["root_hash"] == registry["root_hash"]

    # Save registry
    save_registry(registry)
    assert os.path.exists(REGISTRY_PATH)


@pytest.mark.policy
def test_registry_chain_update(temp_policy_dir, monkeypatch):
    """Test: Registry chain tracks history."""
    monkeypatch.chdir(Path(temp_policy_dir).parent.parent)

    from scripts.policy.registry import update_registry

    # First update
    registry1 = update_registry(temp_policy_dir)
    root_hash_1 = registry1["root_hash"]
    chain_len_1 = len(registry1["chain"])

    # Store registry state
    from scripts.policy.registry import save_registry
    save_registry(registry1)

    # Modify a policy
    policy_file = Path(temp_policy_dir) / "slo.json"
    with open(policy_file, "w", encoding="utf-8") as f:
        json.dump({"budget": {"max_spent": 2000}}, f)

    # Second update
    registry2 = update_registry(temp_policy_dir)
    root_hash_2 = registry2["root_hash"]
    chain_len_2 = len(registry2["chain"])

    # Root hash should change
    assert root_hash_2 != root_hash_1

    # Chain should grow (by at least 1 entry)
    assert chain_len_2 >= chain_len_1 + 1

    # Last chain entry should reference previous
    assert registry2["chain"][-1]["prev_root_hash"] == root_hash_1


@pytest.mark.policy
def test_registry_verify_chain_valid(temp_policy_dir, monkeypatch):
    """Test: Verify chain validates correctly."""
    monkeypatch.chdir(Path(temp_policy_dir).parent.parent)

    from scripts.policy.registry import update_registry, verify_chain

    registry = update_registry(temp_policy_dir)

    # Verify chain
    assert verify_chain(registry) is True


@pytest.mark.policy
def test_registry_verify_chain_broken(temp_policy_dir, monkeypatch):
    """Test: Verify chain detects tampering."""
    monkeypatch.chdir(Path(temp_policy_dir).parent.parent)

    from scripts.policy.registry import update_registry, verify_chain

    # Build chain
    registry = update_registry(temp_policy_dir)

    # Modify policy and update
    policy_file = Path(temp_policy_dir) / "slo.json"
    with open(policy_file, "w", encoding="utf-8") as f:
        json.dump({"budget": {"max_spent": 3000}}, f)

    registry = update_registry(temp_policy_dir)

    # Tamper with chain (break link)
    if len(registry["chain"]) > 1:
        registry["chain"][-1]["prev_root_hash"] = "tampered-hash"

        # Verify chain should fail
        assert verify_chain(registry) is False


@pytest.mark.policy
def test_registry_empty_chain(temp_policy_dir, monkeypatch):
    """Test: Empty chain is valid."""
    monkeypatch.chdir(Path(temp_policy_dir).parent.parent)

    from scripts.policy.registry import verify_chain

    registry = {"chain": []}

    # Empty chain is valid
    assert verify_chain(registry) is True


@pytest.mark.policy
def test_registry_load_existing(temp_policy_dir, monkeypatch):
    """Test: Load existing registry."""
    monkeypatch.chdir(Path(temp_policy_dir).parent.parent)

    from scripts.policy.registry import REGISTRY_PATH, load_registry, save_registry, update_registry

    # Create initial registry
    registry1 = update_registry(temp_policy_dir)
    save_registry(registry1)

    # Load registry
    registry2 = load_registry()

    assert registry2["root_hash"] == registry1["root_hash"]
    assert len(registry2["chain"]) == len(registry1["chain"])
