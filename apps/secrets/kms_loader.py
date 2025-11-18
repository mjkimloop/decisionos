"""
KMS Loader with ENV/SSM overlay, version tracking, grace period, and audit logging.

Priority: ENV > SSM (stored) > cached
Grace period allows stale versions during rotation
"""
import os
import json
import time
import hashlib
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class KeyPolicy:
    """Key rotation policy"""
    key_id: str
    role: str  # e.g., "judge-hmac", "evidence-sign"
    rotation_days: int = 90
    grace_window_sec: int = 120
    allowed_sources: List[str] = field(default_factory=lambda: ["ENV", "SSM"])

@dataclass
class KeyVersion:
    """Key version with metadata"""
    key_id: str
    value: str
    version: str
    source: str  # "ENV" or "SSM"
    loaded_at: float
    hash_prefix: str  # First 8 chars of SHA256 for audit

class KMSLoader:
    """
    Load secrets/keys from ENV and SSM with overlay merge.
    - ENV vars take priority over SSM
    - Tracks version and source for each key
    - Grace period: stale versions remain valid during grace_window_sec
    - Audit log: records key_id, version, source, loaded_at
    """

    def __init__(self, policy_path: str = "configs/secrets/policies.json"):
        self.policy_path = policy_path
        self.policies: Dict[str, KeyPolicy] = {}
        self._load_policies()

        # Active keys: {key_id: KeyVersion}
        self._active_keys: Dict[str, KeyVersion] = {}

        # Grace keys: {key_id: KeyVersion} (old versions still valid)
        self._grace_keys: Dict[str, KeyVersion] = {}

        # Audit log in memory
        self._audit_log: List[Dict[str, Any]] = []

        self._last_load_time: float = 0.0
        self._degraded: bool = False

    def _load_policies(self) -> None:
        """Load rotation policies from config file"""
        if not os.path.exists(self.policy_path):
            print(f"[WARN] Policy file not found: {self.policy_path}, using defaults")
            return

        with open(self.policy_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for key_id, policy_data in data.get("keys", {}).items():
            self.policies[key_id] = KeyPolicy(
                key_id=key_id,
                role=policy_data.get("role", "unknown"),
                rotation_days=policy_data.get("rotation_days", 90),
                grace_window_sec=policy_data.get("grace_window_sec", 120),
                allowed_sources=policy_data.get("allowed_sources", ["ENV", "SSM"])
            )

    def _hash_prefix(self, value: str) -> str:
        """Return first 8 chars of SHA256 for audit"""
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]

    def _load_from_env(self, key_id: str) -> Optional[KeyVersion]:
        """Load key from environment variable"""
        policy = self.policies.get(key_id)
        if policy and "ENV" not in policy.allowed_sources:
            return None

        env_var = f"DECISIONOS_KEY_{key_id.upper().replace('-', '_')}"
        value = os.environ.get(env_var)
        if not value:
            return None

        return KeyVersion(
            key_id=key_id,
            value=value,
            version="env",
            source="ENV",
            loaded_at=time.time(),
            hash_prefix=self._hash_prefix(value)
        )

    def _load_from_ssm(self, key_id: str) -> Optional[KeyVersion]:
        """Load key from SSM Parameter Store (simulated)"""
        policy = self.policies.get(key_id)
        if policy and "SSM" not in policy.allowed_sources:
            return None

        # Simulated SSM loading
        # In production, use boto3 ssm.get_parameter()
        ssm_param = os.environ.get("DECISIONOS_SSM_PARAM_KEYS", "")
        if not ssm_param:
            return None

        # Mock: for testing, we'll check SSM_{key_id} env var
        ssm_var = f"SSM_{key_id.upper().replace('-', '_')}"
        value = os.environ.get(ssm_var)
        if not value:
            return None

        # In production, extract version from SSM metadata
        version = "v1"  # Placeholder

        return KeyVersion(
            key_id=key_id,
            value=value,
            version=version,
            source="SSM",
            loaded_at=time.time(),
            hash_prefix=self._hash_prefix(value)
        )

    def load_key(self, key_id: str) -> Optional[KeyVersion]:
        """
        Load a single key with ENV > SSM priority.
        Updates active keys and moves old version to grace period.
        """
        now = time.time()

        # Try ENV first (higher priority)
        kv = self._load_from_env(key_id)
        if not kv:
            # Fallback to SSM
            kv = self._load_from_ssm(key_id)

        if not kv:
            return None

        # Move current active key to grace period
        if key_id in self._active_keys:
            old_kv = self._active_keys[key_id]
            policy = self.policies.get(key_id, KeyPolicy(key_id=key_id, role="unknown"))

            # Only move to grace if version changed
            if old_kv.version != kv.version or old_kv.hash_prefix != kv.hash_prefix:
                self._grace_keys[key_id] = old_kv
                print(f"[INFO] Key {key_id} rotated: {old_kv.version} -> {kv.version}, grace until {now + policy.grace_window_sec}")

        # Update active key
        self._active_keys[key_id] = kv

        # Audit log
        self._audit_log.append({
            "key_id": key_id,
            "version": kv.version,
            "source": kv.source,
            "loaded_at": datetime.fromtimestamp(kv.loaded_at).isoformat(),
            "hash_prefix": kv.hash_prefix
        })

        return kv

    def get_key(self, key_id: str) -> Optional[str]:
        """
        Get key value by ID.
        Returns active key or grace key (if within grace window).
        """
        # Check active keys first
        if key_id in self._active_keys:
            return self._active_keys[key_id].value

        # Check grace keys
        if key_id in self._grace_keys:
            grace_kv = self._grace_keys[key_id]
            policy = self.policies.get(key_id, KeyPolicy(key_id=key_id, role="unknown"))

            now = time.time()
            grace_expire = grace_kv.loaded_at + policy.grace_window_sec

            if now < grace_expire:
                print(f"[WARN] Using grace key for {key_id}, expires in {grace_expire - now:.1f}s")
                return grace_kv.value
            else:
                # Grace period expired, remove
                del self._grace_keys[key_id]

        return None

    def load_all_keys(self) -> bool:
        """Load all keys defined in policies"""
        success = True
        for key_id in self.policies.keys():
            kv = self.load_key(key_id)
            if not kv:
                print(f"[ERROR] Failed to load key: {key_id}")
                success = False
                self._degraded = True

        if success:
            self._degraded = False

        self._last_load_time = time.time()
        return success

    def refresh(self, force: bool = False) -> bool:
        """Refresh all keys (respects grace period)"""
        return self.load_all_keys()

    def check_stale_versions(self) -> List[str]:
        """Check for keys with stale versions (in grace period)"""
        stale = []
        now = time.time()

        for key_id, grace_kv in self._grace_keys.items():
            policy = self.policies.get(key_id, KeyPolicy(key_id=key_id, role="unknown"))
            grace_expire = grace_kv.loaded_at + policy.grace_window_sec

            if now < grace_expire:
                stale.append(f"{key_id} (grace expires in {grace_expire - now:.1f}s)")

        return stale

    def is_ready(self) -> bool:
        """Check if loader is ready (not degraded)"""
        return not self._degraded

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Return audit log entries"""
        return self._audit_log.copy()

# Factory function
def build_kms_loader(policy_path: str = "configs/secrets/policies.json") -> KMSLoader:
    """Build KMS loader and perform initial load"""
    loader = KMSLoader(policy_path)
    loader.load_all_keys()
    return loader
