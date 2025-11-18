"""
E2E — S3 ObjectLock policy validation (dry run, no AWS required)
"""
import json
import pytest
from pathlib import Path


def test_policy_has_minimum_guards():
    """Test that bucket policy has required security statements"""
    pol_path = Path("configs/s3/object_lock_bucket_policy.json")
    pol = json.loads(pol_path.read_text())

    # Check policy structure
    assert "Version" in pol
    assert "Statement" in pol
    assert isinstance(pol["Statement"], list)

    # Extract statement IDs
    sids = [s.get("Sid") for s in pol["Statement"]]

    # Must have TLS enforcement
    assert "DenyUnEncryptedInTransit" in sids

    # Must have ObjectLock enforcement
    assert any("ObjectLock" in sid for sid in sids if sid)


def test_policy_enforces_tls():
    """Test that policy denies unencrypted transport"""
    pol_path = Path("configs/s3/object_lock_bucket_policy.json")
    pol = json.loads(pol_path.read_text())

    tls_stmt = None
    for stmt in pol["Statement"]:
        if stmt.get("Sid") == "DenyUnEncryptedInTransit":
            tls_stmt = stmt
            break

    assert tls_stmt is not None
    assert tls_stmt["Effect"] == "Deny"
    assert "aws:SecureTransport" in str(tls_stmt.get("Condition", {}))


def test_policy_enforces_object_lock():
    """Test that policy enforces ObjectLock"""
    pol_path = Path("configs/s3/object_lock_bucket_policy.json")
    pol = json.loads(pol_path.read_text())

    lock_stmt = None
    for stmt in pol["Statement"]:
        if "ObjectLock" in stmt.get("Sid", ""):
            lock_stmt = stmt
            break

    assert lock_stmt is not None
    assert lock_stmt["Effect"] == "Deny"

    # Check that dangerous actions are denied
    actions = lock_stmt.get("Action", [])
    assert "s3:DeleteObject" in actions or "s3:DeleteObject" in str(actions)


def test_lifecycle_has_wip_and_locked_rules():
    """Test that lifecycle config has WIP and LOCKED tier rules"""
    lc_path = Path("configs/s3/lifecycle_lock.json")
    lc = json.loads(lc_path.read_text())

    assert "Rules" in lc
    assert isinstance(lc["Rules"], list)

    rule_ids = [r.get("ID") for r in lc["Rules"]]

    # Must have WIP tier rule
    assert any("WIP" in rid for rid in rule_ids if rid)

    # Must have LOCKED tier rule
    assert any("LOCKED" in rid for rid in rule_ids if rid)


def test_lifecycle_wip_expires():
    """Test that WIP tier has expiration"""
    lc_path = Path("configs/s3/lifecycle_lock.json")
    lc = json.loads(lc_path.read_text())

    wip_rule = None
    for rule in lc["Rules"]:
        if "WIP" in rule.get("ID", ""):
            wip_rule = rule
            break

    assert wip_rule is not None
    assert wip_rule["Status"] == "Enabled"
    assert "Expiration" in wip_rule
    assert wip_rule["Expiration"]["Days"] > 0


def test_lifecycle_locked_retains():
    """Test that LOCKED tier retains for long period"""
    lc_path = Path("configs/s3/lifecycle_lock.json")
    lc = json.loads(lc_path.read_text())

    locked_rule = None
    for rule in lc["Rules"]:
        rule_id = rule.get("ID", "")
        # Check for exact match to avoid matching "WIP-to-LOCKED"
        if rule_id == "LOCKED-retain":
            locked_rule = rule
            break

    assert locked_rule is not None
    assert locked_rule["Status"] == "Enabled"

    # LOCKED tier should have noncurrent version expiration (long retention)
    assert "NoncurrentVersionExpiration" in locked_rule
    assert locked_rule["NoncurrentVersionExpiration"]["NoncurrentDays"] >= 365
