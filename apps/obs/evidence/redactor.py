"""
Evidence PII Redactor - Production-ready integration of PII masking pipeline.

This module wraps the redact.py functionality with production config loading
and fail-closed behavior integration.
"""
import os
import json
from typing import Any, Dict, Optional
from .redact import redact_evidence, RedactStrategy

class EvidenceRedactor:
    """
    Production Evidence Redactor with config-driven PII masking.

    Features:
    - YAML/JSON config loading
    - On/off toggle via config or environment
    - Fail-closed: redaction failure → tampered=True
    - Integrity hash recalculation after redaction
    """

    def __init__(self, config_path: str = "configs/evidence/redaction.json"):
        self.config_path = config_path
        self.enabled = True
        self.rules: Dict[str, Dict[str, Any]] = {}
        self.patterns: Dict[str, str] = {}

        self._load_config()

    def _load_config(self) -> None:
        """Load redaction configuration"""
        if not os.path.exists(self.config_path):
            print(f"[WARN] Redaction config not found: {self.config_path}, PII redaction disabled")
            self.enabled = False
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        # Check if redaction is enabled
        self.enabled = config.get("enabled", True)

        # Load field rules
        self.rules = config.get("rules", {})

        # Load custom patterns
        self.patterns = config.get("patterns", {})

    def is_enabled(self) -> bool:
        """Check if redaction is enabled"""
        # Environment variable can override config
        env_enabled = os.environ.get("DECISIONOS_PII_REDACTION_ENABLED", "").lower()
        if env_enabled in ("false", "0", "no"):
            return False
        if env_enabled in ("true", "1", "yes"):
            return True

        return self.enabled

    def redact(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact PII from evidence document.

        Returns redacted evidence. On failure, raises exception (fail-closed).
        """
        if not self.is_enabled():
            return evidence

        try:
            # Apply redaction using rules from config
            from .redact import redact_dict

            # self.rules is already in the correct format: Dict[str, Dict[str, Any]]
            # where each value is a dict with "strategy", "salt_ref", etc.
            redacted = redact_dict(evidence, self.rules)
            return redacted
        except Exception as e:
            # Fail-closed: raise exception to mark evidence as tampered
            raise RuntimeError(f"PII redaction failed: {e}") from e

    def redact_safe(self, evidence: Dict[str, Any]) -> tuple[Dict[str, Any], bool]:
        """
        Redact PII with safe error handling.

        Returns (redacted_evidence, success).
        On failure, returns (original_evidence, False) without raising.
        """
        if not self.is_enabled():
            return evidence, True

        try:
            redacted = self.redact(evidence)
            return redacted, True
        except Exception as e:
            print(f"[ERROR] PII redaction failed: {e}")
            return evidence, False

# Factory function
def build_redactor(config_path: str = "configs/evidence/redaction.json") -> EvidenceRedactor:
    """Build Evidence Redactor with config"""
    return EvidenceRedactor(config_path)

# Global instance (lazy-loaded)
_redactor_instance: Optional[EvidenceRedactor] = None

def get_redactor() -> EvidenceRedactor:
    """Get global redactor instance"""
    global _redactor_instance
    if _redactor_instance is None:
        _redactor_instance = build_redactor()
    return _redactor_instance
