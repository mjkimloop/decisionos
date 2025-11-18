#!/usr/bin/env python3
"""Policy verification tool: Signature, chain, and allowlist validation.

Usage:
    python -m scripts.policy.verify <policy_file>
    python -m scripts.policy.verify --batch configs/policy/*.json
    python -m scripts.policy.verify --strict <policy_file>  # Fail on any error

Environment:
    DECISIONOS_POLICY_KEYS_JSON: MultiKey HMAC config
    DECISIONOS_POLICY_ALLOWLIST: Comma-separated allowed key_ids (optional)
    DECISIONOS_POLICY_FAIL_OPEN: "1" to allow unsigned (default "0")

Exit codes:
    0: All checks passed
    1: Verification failed (strict mode)
    8: Warnings present (soft fail)
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _sha256_file(path: str) -> str:
    """Compute SHA256 hash of file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def _load_hmac_keys() -> List[Dict[str, Any]]:
    """Load HMAC keys from environment (active + grace)."""
    keys_json = os.environ.get("DECISIONOS_POLICY_KEYS_JSON", "[]")
    try:
        keys = json.loads(keys_json)
        # Allow both active and grace keys for verification
        return [k for k in keys if k.get("state") in ("active", "grace")]
    except json.JSONDecodeError:
        return []


def _verify_hmac(payload: bytes, sig_b64: str, key_id: str) -> Tuple[bool, str]:
    """Verify HMAC signature.

    Returns:
        (is_valid, error_message)
    """
    keys = _load_hmac_keys()
    key = next((k for k in keys if k["key_id"] == key_id), None)

    if not key:
        return False, f"Key not found: {key_id}"

    try:
        secret = base64.b64decode(key["secret"])
        expected_sig = hmac.new(secret, payload, hashlib.sha256).digest()
        actual_sig = base64.b64decode(sig_b64)

        if hmac.compare_digest(expected_sig, actual_sig):
            return True, ""
        else:
            return False, "Signature mismatch"
    except Exception as e:
        return False, f"Verification error: {e}"


def _verify_kms(payload: bytes, sig_b64: str, kms_arn: str) -> Tuple[bool, str]:
    """Verify KMS signature (stub)."""
    # Production would use boto3.client('kms').verify()
    return False, "KMS verification not yet implemented"


def load_signature(policy_path: str) -> Optional[Dict[str, Any]]:
    """Load .sig file for policy."""
    sig_path = f"{policy_path}.sig"
    if not os.path.exists(sig_path):
        return None

    try:
        with open(sig_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def verify_signature(policy_path: str, sig_data: Dict[str, Any]) -> Tuple[bool, str]:
    """Verify signature matches policy file.

    Returns:
        (is_valid, error_message)
    """
    # Recompute file hash
    actual_hash = _sha256_file(policy_path)
    expected_hash = sig_data.get("sha256", "")

    if actual_hash != expected_hash:
        return False, f"Hash mismatch: expected {expected_hash}, got {actual_hash}"

    # Verify signature
    algorithm = sig_data.get("algorithm", "")
    signature = sig_data.get("signature", "")
    payload = expected_hash.encode("utf-8")

    if algorithm == "hmac-sha256":
        key_id = sig_data.get("key_id", "")
        return _verify_hmac(payload, signature, key_id)
    elif algorithm == "kms-rsa-sha256":
        kms_arn = sig_data.get("kms_arn", "")
        return _verify_kms(payload, signature, kms_arn)
    else:
        return False, f"Unknown algorithm: {algorithm}"


def check_allowlist(sig_data: Dict[str, Any]) -> Tuple[bool, str]:
    """Check if key_id is in allowlist.

    Returns:
        (is_allowed, error_message)
    """
    allowlist_str = os.environ.get("DECISIONOS_POLICY_ALLOWLIST", "")
    if not allowlist_str:
        # No allowlist = allow all
        return True, ""

    allowlist = [k.strip() for k in allowlist_str.split(",")]
    key_id = sig_data.get("key_id", "")

    if key_id in allowlist:
        return True, ""
    else:
        return False, f"Key not in allowlist: {key_id}"


def verify_file(
    policy_path: str, strict: bool = False, fail_open: bool = False
) -> Tuple[bool, List[str]]:
    """Verify single policy file.

    Args:
        policy_path: Path to policy file
        strict: Fail hard on any error
        fail_open: Allow unsigned files (default False)

    Returns:
        (passed, warnings)
    """
    warnings = []

    # Check if signature exists
    sig_data = load_signature(policy_path)
    if not sig_data:
        if fail_open:
            warnings.append(f"No signature found: {policy_path} (allowed by fail-open)")
            return True, warnings
        else:
            return False, [f"No signature found: {policy_path}"]

    # Verify signature
    valid, err = verify_signature(policy_path, sig_data)
    if not valid:
        return False, [f"Signature verification failed: {err}"]

    # Check allowlist
    allowed, err = check_allowlist(sig_data)
    if not allowed:
        if strict:
            return False, [f"Allowlist check failed: {err}"]
        else:
            warnings.append(f"Allowlist warning: {err}")

    return True, warnings


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Verify policy signatures")
    parser.add_argument("files", nargs="+", help="Policy files to verify")
    parser.add_argument("--strict", action="store_true", help="Fail on any error")
    parser.add_argument("--batch", action="store_true", help="Batch mode (glob patterns)")
    parser.add_argument("--fail-open", action="store_true", help="Allow unsigned files")

    args = parser.parse_args()

    # Expand globs if batch mode
    files = []
    if args.batch:
        from glob import glob

        for pattern in args.files:
            files.extend(glob(pattern))
    else:
        files = args.files

    if not files:
        print("No files to verify", file=sys.stderr)
        return 1

    # Check fail-open from env
    fail_open = args.fail_open or os.environ.get("DECISIONOS_POLICY_FAIL_OPEN") == "1"

    passed_count = 0
    all_warnings = []

    for policy_file in files:
        passed, warnings = verify_file(policy_file, args.strict, fail_open)

        if passed:
            print(f"✓ Verified: {policy_file}")
            passed_count += 1
            all_warnings.extend(warnings)
        else:
            print(f"✗ Failed: {policy_file}", file=sys.stderr)
            for w in warnings:
                print(f"  {w}", file=sys.stderr)

    # Print summary
    print(f"\nVerified {passed_count}/{len(files)} files")

    if all_warnings:
        print(f"Warnings: {len(all_warnings)}")
        for w in all_warnings:
            print(f"  ⚠ {w}")

    # Exit codes
    if passed_count < len(files):
        return 1  # Hard fail
    elif all_warnings:
        return 8  # Soft fail (warnings)
    else:
        return 0  # Success


if __name__ == "__main__":
    sys.exit(main())
