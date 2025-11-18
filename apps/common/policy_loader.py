from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from apps.judge.crypto import MultiKeyLoader, hmac_sign_canonical


class PolicySignatureError(RuntimeError):
    pass


class PolicyLoader:
    """Loads and verifies signed policy files (YAML/JSON) with fail-closed enforcement.

    Features:
    - Signature verification (HMAC-SHA256)
    - Key allowlist enforcement (DECISIONOS_POLICY_ALLOWLIST)
    - Scope-based access control (DECISIONOS_ALLOW_SCOPES)
    - Fail-closed by default (DECISIONOS_POLICY_FAIL_OPEN=0)
    """

    def __init__(
        self,
        *,
        env_var: str = "DECISIONOS_POLICY_KEYS",
        file_env: str = "DECISIONOS_POLICY_KEYS_FILE",
        fail_open: Optional[bool] = None,
    ) -> None:
        self._loader = MultiKeyLoader(env_var=env_var, file_env=file_env)
        self._loader.force_reload()

        # Determine fail-open mode from env if not specified
        if fail_open is None:
            fail_open = os.environ.get("DECISIONOS_POLICY_FAIL_OPEN") == "1"
        self._fail_open = fail_open

    def _canonical(self, data: Any) -> str:
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    def _check_allowlist(self, key_id: str) -> None:
        """Check if key_id is in allowlist (if configured)."""
        allowlist_str = os.environ.get("DECISIONOS_POLICY_ALLOWLIST", "")
        if not allowlist_str:
            # No allowlist = allow all
            return

        allowlist = [k.strip() for k in allowlist_str.split(",")]
        if key_id not in allowlist:
            raise PolicySignatureError(f"Key not in allowlist: {key_id}")

    def _verify_signature(self, data: Any, sig_path: Path) -> Tuple[str, str]:
        if not sig_path.exists():
            if self._fail_open:
                # Fail-open mode: allow unsigned files with warning
                import sys
                print(f"Warning: No signature for {sig_path.with_suffix('')} (fail-open mode)", file=sys.stderr)
                return "", ""
            raise PolicySignatureError(f"signature missing for {sig_path.with_suffix('')}")

        try:
            sig_data = json.loads(sig_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover
            raise PolicySignatureError(f"signature invalid json: {sig_path}") from exc

        key_id = sig_data.get("key_id")
        expected = sig_data.get("hmac_sha256")
        if not key_id or not expected:
            raise PolicySignatureError(f"signature missing key_id/hmac: {sig_path}")

        # Check allowlist
        self._check_allowlist(key_id)

        material = self._loader.get(key_id)
        if not material:
            raise PolicySignatureError(f"unknown policy key_id={key_id}")

        computed = hmac_sign_canonical(data, material.secret)
        if computed != expected:
            raise PolicySignatureError(f"signature mismatch for {sig_path}")

        return key_id, expected

    def load(self, path: str, *, scope: Optional[str] = None) -> Dict[str, Any]:
        """Load and verify policy file.

        Args:
            path: Path to policy file
            scope: Required scope (checked against DECISIONOS_ALLOW_SCOPES if set)

        Returns:
            Parsed policy dict

        Raises:
            PolicySignatureError: If verification fails
            FileNotFoundError: If policy file not found
        """
        # Check scope restriction
        if scope:
            allowed_scopes = os.environ.get("DECISIONOS_ALLOW_SCOPES", "")
            if allowed_scopes:
                scopes = [s.strip() for s in allowed_scopes.split(",")]
                if scope not in scopes:
                    raise PolicySignatureError(
                        f"Scope '{scope}' not in DECISIONOS_ALLOW_SCOPES: {allowed_scopes}"
                    )

        file = Path(path)
        if not file.exists():
            raise FileNotFoundError(path)

        if file.suffix in (".json", ".signed"):
            raw = json.loads(file.read_text(encoding="utf-8"))
        else:
            raw = yaml.safe_load(file.read_text(encoding="utf-8"))

        sig_path = Path(f"{path}.sig")
        self._verify_signature(raw, sig_path)

        return raw


_POLICY_LOADER: Optional[PolicyLoader] = None


def _get_loader() -> PolicyLoader:
    global _POLICY_LOADER
    if _POLICY_LOADER is None:
        _POLICY_LOADER = PolicyLoader()
    return _POLICY_LOADER


def load_freeze_policy(path: str = "configs/change/freeze_windows.yaml") -> Dict[str, Any]:
    data = _get_loader().load(path)
    if "windows" not in data or not isinstance(data["windows"], list):
        raise PolicySignatureError("freeze policy missing windows array")
    return data


def load_ownership_policy(path: str = "configs/change/ownership.yaml") -> Dict[str, Any]:
    data = _get_loader().load(path)
    if "services" not in data or not isinstance(data["services"], list):
        raise PolicySignatureError("ownership policy missing services")
    return data


def load_approval_policy(path: str = "configs/policy/approval_policies.yaml") -> Dict[str, Any]:
    data = _get_loader().load(path)
    if "rules" not in data or not isinstance(data["rules"], list):
        raise PolicySignatureError("approval policy missing rules")
    return data


__all__ = [
    "PolicyLoader",
    "PolicySignatureError",
    "load_freeze_policy",
    "load_ownership_policy",
    "load_approval_policy",
]
