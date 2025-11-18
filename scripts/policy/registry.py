#!/usr/bin/env python3
"""Policy registry: Index and hash chain management.

Maintains configs/policy/registry.json with:
- root_hash: SHA256 of all policy hashes combined
- entries: [{file, sha256, key_id, created_at}]
- allowed_keys: [{key_id, state, added_at}]
- chain: [{root_hash, timestamp, prev_root_hash}]

Usage:
    python -m scripts.policy.registry update
    python -m scripts.policy.registry verify-chain
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ISO = "%Y-%m-%dT%H:%M:%SZ"
REGISTRY_PATH = "configs/policy/registry.json"


def _sha256_file(path: str) -> str:
    """Compute SHA256 hash of file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def _compute_root_hash(entries: List[Dict[str, Any]]) -> str:
    """Compute root hash from all policy file hashes."""
    if not entries:
        return ""

    # Sort entries by filename for deterministic hash
    sorted_entries = sorted(entries, key=lambda e: e["file"])
    combined = "".join(e["sha256"] for e in sorted_entries)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def load_registry() -> Dict[str, Any]:
    """Load existing registry or create new one."""
    if os.path.exists(REGISTRY_PATH):
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Default empty registry
    return {
        "version": 1,
        "root_hash": "",
        "entries": [],
        "allowed_keys": [],
        "chain": [],
    }


def save_registry(registry: Dict[str, Any]) -> None:
    """Save registry to file."""
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


def scan_policies(policy_dir: str = "configs/policy") -> List[Dict[str, Any]]:
    """Scan policy directory and build entries list."""
    entries = []

    if not os.path.exists(policy_dir):
        return entries

    for policy_file in Path(policy_dir).glob("*.json"):
        # Skip registry itself
        if policy_file.name == "registry.json":
            continue

        # Load signature if exists
        sig_path = f"{policy_file}.sig"
        sig_data = None
        if os.path.exists(sig_path):
            try:
                with open(sig_path, "r", encoding="utf-8") as f:
                    sig_data = json.load(f)
            except Exception:
                pass

        # Compute hash
        file_hash = _sha256_file(str(policy_file))

        entry = {
            "file": policy_file.name,
            "sha256": file_hash,
            "key_id": sig_data.get("key_id", "") if sig_data else "",
            "created_at": sig_data.get("created_at", "") if sig_data else "",
        }

        entries.append(entry)

    return entries


def update_registry(policy_dir: str = "configs/policy") -> Dict[str, Any]:
    """Update registry with current policy state."""
    registry = load_registry()

    # Scan policies
    entries = scan_policies(policy_dir)

    # Compute new root hash
    new_root_hash = _compute_root_hash(entries)

    # Add to chain if root hash changed
    if new_root_hash != registry.get("root_hash"):
        chain_entry = {
            "root_hash": new_root_hash,
            "timestamp": datetime.now(timezone.utc).strftime(ISO),
            "prev_root_hash": registry.get("root_hash", ""),
        }
        registry.setdefault("chain", []).append(chain_entry)

    # Update registry
    registry["root_hash"] = new_root_hash
    registry["entries"] = entries
    registry["updated_at"] = datetime.now(timezone.utc).strftime(ISO)

    # Update allowed_keys from environment
    keys_json = os.environ.get("DECISIONOS_POLICY_KEYS_JSON", "[]")
    try:
        keys = json.loads(keys_json)
        allowed_keys = []
        for k in keys:
            if k.get("state") in ("active", "grace"):
                allowed_keys.append(
                    {
                        "key_id": k["key_id"],
                        "state": k["state"],
                        "added_at": k.get("not_before", ""),
                    }
                )
        registry["allowed_keys"] = allowed_keys
    except Exception:
        pass

    return registry


def verify_chain(registry: Dict[str, Any]) -> bool:
    """Verify hash chain integrity.

    Returns:
        True if chain is valid
    """
    chain = registry.get("chain", [])
    if not chain:
        return True  # Empty chain is valid

    # Check each link
    for i in range(1, len(chain)):
        prev = chain[i - 1]
        curr = chain[i]

        if curr.get("prev_root_hash") != prev.get("root_hash"):
            print(
                f"Chain break at index {i}: prev_root_hash mismatch",
                file=sys.stderr,
            )
            return False

    # Check current root_hash matches last chain entry
    if chain[-1].get("root_hash") != registry.get("root_hash"):
        print(
            "Registry root_hash does not match last chain entry",
            file=sys.stderr,
        )
        return False

    return True


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage policy registry")
    parser.add_argument(
        "command",
        choices=["update", "verify-chain", "show"],
        help="Command to execute",
    )
    parser.add_argument(
        "--policy-dir",
        default="configs/policy",
        help="Policy directory (default: configs/policy)",
    )

    args = parser.parse_args()

    if args.command == "update":
        registry = update_registry(args.policy_dir)
        save_registry(registry)
        print(f"✓ Registry updated: {REGISTRY_PATH}")
        print(f"  Root hash: {registry['root_hash']}")
        print(f"  Entries: {len(registry['entries'])}")
        print(f"  Chain length: {len(registry.get('chain', []))}")
        return 0

    elif args.command == "verify-chain":
        registry = load_registry()
        if verify_chain(registry):
            print("✓ Chain verified")
            return 0
        else:
            print("✗ Chain verification failed", file=sys.stderr)
            return 1

    elif args.command == "show":
        registry = load_registry()
        print(json.dumps(registry, indent=2, ensure_ascii=False))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
