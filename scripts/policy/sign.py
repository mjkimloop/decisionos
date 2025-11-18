#!/usr/bin/env python3
"""Policy signing tool: HMAC or KMS-based signature generation.

Usage:
    python -m scripts.policy.sign <policy_file> [--key-id KEY_ID] [--kms-arn ARN]
    python -m scripts.policy.sign --batch configs/policy/*.json

Environment:
    DECISIONOS_POLICY_KEYS_JSON: MultiKey HMAC config (default)
    DECISIONOS_POLICY_KMS_KEY_ARN: KMS key ARN (overrides HMAC)

Output:
    <policy_file>.sig: JSON signature file with metadata
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ISO = "%Y-%m-%dT%H:%M:%SZ"


def _sha256_file(path: str) -> str:
    """Compute SHA256 hash of file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def _load_hmac_keys() -> List[Dict[str, Any]]:
    """Load HMAC keys from environment."""
    keys_json = os.environ.get("DECISIONOS_POLICY_KEYS_JSON", "[]")
    try:
        keys = json.loads(keys_json)
        # Allow both active and grace keys for signing
        return [k for k in keys if k.get("state") in ("active", "grace")]
    except json.JSONDecodeError:
        return []


def _sign_hmac(payload: bytes, key_id: Optional[str] = None) -> Dict[str, Any]:
    """Sign payload using HMAC with MultiKey."""
    keys = _load_hmac_keys()
    if not keys:
        raise ValueError("No active HMAC keys found in DECISIONOS_POLICY_KEYS_JSON")

    # Select key by key_id or use first active
    if key_id:
        key = next((k for k in keys if k["key_id"] == key_id), None)
        if not key:
            raise ValueError(f"Key not found: {key_id}")
    else:
        key = keys[0]

    secret = base64.b64decode(key["secret"])
    sig = hmac.new(secret, payload, hashlib.sha256).digest()

    return {
        "algorithm": "hmac-sha256",
        "key_id": key["key_id"],
        "signature": base64.b64encode(sig).decode("ascii"),
    }


def _sign_kms(payload: bytes, kms_arn: str) -> Dict[str, Any]:
    """Sign payload using AWS KMS (stub - requires boto3)."""
    # Production implementation would use boto3.client('kms').sign()
    # For now, raise NotImplementedError to indicate KMS support is planned
    raise NotImplementedError(
        f"KMS signing not yet implemented. Requested KMS ARN: {kms_arn}\n"
        "To enable KMS support, install boto3 and configure AWS credentials."
    )


def sign_file(
    policy_path: str,
    key_id: Optional[str] = None,
    kms_arn: Optional[str] = None,
    issuer: str = "platform",
) -> Dict[str, Any]:
    """Sign policy file and return signature metadata.

    Args:
        policy_path: Path to policy file
        key_id: HMAC key ID (optional, uses first active if not specified)
        kms_arn: KMS key ARN (overrides HMAC)
        issuer: Signature issuer name

    Returns:
        Signature metadata dict
    """
    # Read and hash file
    with open(policy_path, "rb") as f:
        content = f.read()

    file_hash = _sha256_file(policy_path)

    # Sign payload (file_hash as canonical representation)
    payload = file_hash.encode("utf-8")

    if kms_arn:
        sig_meta = _sign_kms(payload, kms_arn)
    else:
        sig_meta = _sign_hmac(payload, key_id)

    # Build signature file
    sig_data = {
        "version": 1,
        "issuer": issuer,
        "created_at": datetime.now(timezone.utc).strftime(ISO),
        "policy_file": os.path.basename(policy_path),
        "sha256": file_hash,
        **sig_meta,
    }

    return sig_data


def write_signature(policy_path: str, sig_data: Dict[str, Any]) -> str:
    """Write signature to .sig file."""
    sig_path = f"{policy_path}.sig"
    with open(sig_path, "w", encoding="utf-8") as f:
        json.dump(sig_data, f, indent=2, ensure_ascii=False)
    return sig_path


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Sign policy files")
    parser.add_argument("files", nargs="+", help="Policy files to sign")
    parser.add_argument("--key-id", help="HMAC key ID (optional)")
    parser.add_argument("--kms-arn", help="KMS key ARN (overrides HMAC)")
    parser.add_argument("--issuer", default="platform", help="Signature issuer")
    parser.add_argument("--batch", action="store_true", help="Batch mode (glob patterns)")

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
        print("No files to sign", file=sys.stderr)
        return 1

    # Check KMS ARN from env if not specified
    kms_arn = args.kms_arn or os.environ.get("DECISIONOS_POLICY_KMS_KEY_ARN")

    success_count = 0
    for policy_file in files:
        try:
            sig_data = sign_file(policy_file, args.key_id, kms_arn, args.issuer)
            sig_path = write_signature(policy_file, sig_data)
            print(f"✓ Signed: {policy_file} → {sig_path}")
            success_count += 1
        except Exception as e:
            print(f"✗ Failed to sign {policy_file}: {e}", file=sys.stderr)

    print(f"\nSigned {success_count}/{len(files)} files")
    return 0 if success_count == len(files) else 1


if __name__ == "__main__":
    sys.exit(main())
