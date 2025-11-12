"""
Key Loader Refresh
KMS/SSM 키 주기적 리프레시 + 그레이스 윈도
"""
from __future__ import annotations
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional


@dataclass
class KeyRefreshConfig:
    refresh_interval_sec: int = 300  # 5분마다 리프레시
    grace_window_sec: int = 60       # 1분 그레이스 윈도 (구 키 유지)
    ssm_timeout_sec: float = 2.0     # SSM 타임아웃
    max_retries: int = 3


class KeyLoader:
    """
    Multi-source key loader with refresh and grace period

    Sources priority: ENV > SSM > cached
    """

    def __init__(self, config: Optional[KeyRefreshConfig] = None):
        self.config = config or KeyRefreshConfig()
        self._keys: Dict[str, str] = {}
        self._keys_timestamp: float = 0.0
        self._grace_keys: Dict[str, str] = {}  # Old keys in grace period
        self._grace_expire: float = 0.0
        self._degraded: bool = False

    def _load_from_env(self) -> Dict[str, str]:
        """Load keys from environment variables"""
        keys = {}
        judge_keys = os.environ.get("DECISIONOS_JUDGE_KEYS", "")

        if not judge_keys:
            return keys

        # Format: "k1:secret1,k2:secret2"
        for pair in judge_keys.split(","):
            if ":" in pair:
                key_id, secret = pair.split(":", 1)
                keys[key_id.strip()] = secret.strip()

        return keys

    def _load_from_ssm(self) -> Dict[str, str]:
        """Load keys from AWS SSM Parameter Store"""
        keys = {}

        try:
            import boto3
            from botocore.config import Config

            ssm_path = os.environ.get("DECISIONOS_SSM_KEY_PATH", "/decisionos/judge/keys")
            region = os.environ.get("AWS_REGION", "ap-northeast-2")

            config = Config(
                connect_timeout=self.config.ssm_timeout_sec,
                read_timeout=self.config.ssm_timeout_sec,
                retries={"max_attempts": 1}
            )

            ssm = boto3.client("ssm", region_name=region, config=config)

            response = ssm.get_parameters_by_path(
                Path=ssm_path,
                Recursive=False,
                WithDecryption=True
            )

            for param in response.get("Parameters", []):
                name = param["Name"].split("/")[-1]
                keys[name] = param["Value"]

        except ImportError:
            # boto3 not installed
            pass
        except Exception as e:
            print(f"[WARN] SSM load failed: {e}")
            self._degraded = True

        return keys

    def refresh(self) -> bool:
        """
        Refresh keys from sources

        Returns:
            True if refresh successful, False if degraded
        """
        now = time.time()

        # Check if refresh needed
        if now - self._keys_timestamp < self.config.refresh_interval_sec:
            return not self._degraded

        # Move current keys to grace period
        if self._keys:
            self._grace_keys = self._keys.copy()
            self._grace_expire = now + self.config.grace_window_sec

        # Load from sources (priority: ENV > SSM)
        env_keys = self._load_from_env()
        ssm_keys = self._load_from_ssm()

        # Merge with priority
        new_keys = {}
        new_keys.update(ssm_keys)  # Lower priority
        new_keys.update(env_keys)  # Higher priority

        if not new_keys:
            print("[ERROR] No keys loaded from any source")
            self._degraded = True
            return False

        self._keys = new_keys
        self._keys_timestamp = now
        self._degraded = False

        return True

    def get_key(self, key_id: str) -> Optional[str]:
        """
        Get key by ID (with grace period support)

        Args:
            key_id: Key identifier

        Returns:
            Key secret or None
        """
        # Try current keys first
        if key_id in self._keys:
            return self._keys[key_id]

        # Check grace period keys
        now = time.time()
        if now < self._grace_expire and key_id in self._grace_keys:
            return self._grace_keys[key_id]

        return None

    def get_all_keys(self) -> Dict[str, str]:
        """Get all current keys"""
        return self._keys.copy()

    def is_degraded(self) -> bool:
        """Check if loader is in degraded state"""
        return self._degraded

    def readiness_check(self) -> Dict[str, any]:
        """
        Readiness check for health endpoint

        Returns:
            Status dict with healthy/degraded state
        """
        now = time.time()
        age_sec = now - self._keys_timestamp

        status = {
            "healthy": not self._degraded and len(self._keys) > 0,
            "degraded": self._degraded,
            "keys_count": len(self._keys),
            "grace_keys_count": len(self._grace_keys) if now < self._grace_expire else 0,
            "age_sec": age_sec,
            "next_refresh_sec": max(0, self.config.refresh_interval_sec - age_sec)
        }

        return status


# Global instance
_loader: Optional[KeyLoader] = None


def get_key_loader(config: Optional[KeyRefreshConfig] = None) -> KeyLoader:
    """Get or create global key loader instance"""
    global _loader
    if _loader is None:
        _loader = KeyLoader(config)
    return _loader
