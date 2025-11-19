# apps/config/settings.py
"""
Application settings with Pydantic v2 BaseSettings (v0.5.11u-15a).

Environment variables with DECISIONOS_ prefix.
"""
from __future__ import annotations

from typing import List, Optional

from apps.common.pydantic_compat import BaseSettings, PYDANTIC_V2

if PYDANTIC_V2:
    from pydantic import Field
else:
    from pydantic import Field


class Settings(BaseSettings):
    """DecisionOS application settings."""

    # Core / Ops
    ENV: str = Field(default="dev", description="Environment: dev, staging, prod")
    TENANT: Optional[str] = Field(default=None, description="Tenant ID for multi-tenancy")
    SLACK_WEBHOOK: Optional[str] = None
    SLACK_CHANNEL_OVERRIDE: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # Evidence & S3
    S3_MODE: str = Field(default="stub", description="S3 mode: stub or aws")
    S3_BUCKET: str = "decisionos-evidence"
    S3_PREFIX: str = "evidence/"
    S3_STUB_ROOT: str = "var/s3_stub"
    S3_DRY_RUN: int = 0
    S3_OBJECTLOCK_MODE: str = "GOVERNANCE"
    S3_OBJECTLOCK_RETENTION_DAYS: int = 30
    S3_UPLOAD_ONLY_LOCKED: int = 1

    # Evidence Index/GC/DR
    EVIDENCE_DIR: str = "var/evidence"
    EVIDENCE_INDEX: str = "var/evidence/index.json"
    DR_POLICY_PATH: str = "configs/dr/sample_policy.json"
    DR_DEST: str = "var/evidence/restore"
    DR_DRY_RUN: int = 0

    # Cards API / Dashboard
    CARDS_TTL: int = 60
    TOP_IMPACT_N: int = 5

    # Security
    ALLOW_SCOPES: str = "ops:read judge:run deploy:promote deploy:abort"
    SECURITY_HEADERS_ENABLE: int = 0
    PII_ENABLE: int = 0
    PII_MODE: str = "soft"  # soft|hard
    TRUSTED_PROXY_CIDRS: str = ""
    ALLOWED_HOSTS: str = ""
    JUDGE_ALLOWED_HOSTS: str = ""
    RL_ENABLE: int = 0
    RL_BACKEND: str = "memory"
    REDIS_DSN: str = ""
    READY_FAIL_CLOSED: int = 1

    # RBAC
    RBAC_MAP: str = ""
    RBAC_MAP_PATH: str = "configs/security/rbac_map.yaml"
    RBAC_DEFAULT_DENY: int = 0
    RBAC_RELOAD_SEC: int = 2
    RBAC_TEST_MODE: int = Field(default=0, description="Test mode: 0 in production")
    RBAC_MODE: str = "OR"  # OR|AND
    RBAC_BYPASS_PREFIXES: str = "/healthz,/readyz,/metrics"

    # CORS (v0.5.11u-5)
    CORS_ALLOWLIST: str = Field(
        default="",
        description="Comma-separated allowed origins. Production MUST have explicit list."
    )

    # Compression (v0.5.11u-7)
    COMPRESS_ENABLE: int = 1
    COMPRESS_MIN_BYTES: int = 4096
    GZIP_LEVEL: int = 6
    SNAPSHOT_COMPRESS: int = 1
    S3_COMPRESS: int = 1

    # ETag/Snapshot backends
    ETAG_BACKEND: str = "memory"  # memory|redis
    SNAPSHOT_BACKEND: str = "memory"  # memory|redis
    SNAPSHOT_TTL: int = 600
    DELTA_FORCE_FULL_PROBE_PCT: int = 1

    # Alerts
    ALERT_P95_MS: int = 250
    ALERT_RETRY_RATE: float = 0.05
    ALERT_ETAG_HIT_MIN: float = 0.60

    # Consent
    CONSENT_BACKEND: str = "memory"
    CONSENT_SQLITE_PATH: str = "var/consent.db"
    CONSENT_REDIS_DSN: str = ""

    # Executor
    EXECUTOR_BACKEND: str = "memory"
    EXEC_HTTP_TIMEOUT: int = 5
    EXEC_HTTP_RETRIES: int = 1
    EXEC_HTTP_BACKOFF_BASE: float = 0.1
    EXEC_HTTP_HMAC_KEY: str = ""
    EXEC_HTTP_KEY_ID: str = "decisionos"
    EXEC_HTTP_RETRY_NON_IDEMPOTENT: int = 0
    EXEC_HTTP_MASK_FIELDS: str = "password,secret,token"

    # Label catalog
    LABEL_CATALOG: str = "configs/labels/label_catalog_v2.json"
    LABEL_CATALOG_SHA: str = ""

    # Policy keys (JSON array)
    POLICY_KEYS: str = '[]'

    # SSM parameter paths
    SSM_PARAM_JUDGE_KEYS: str = "/decisionos/judge/keys"

    # Helpers
    def get_cors_origins(self) -> List[str]:
        """Parse CORS_ALLOWLIST into list of origins."""
        if not self.CORS_ALLOWLIST:
            # Production: empty CORS list is not allowed
            if self.ENV.lower() == "prod":
                raise ValueError(
                    "CORS_ALLOWLIST must be explicit in production (no wildcard). "
                    "Cannot be empty in production."
                )
            # Dev default
            if self.ENV == "dev":
                return ["http://localhost:3000", "http://127.0.0.1:3000"]
            return []

        origins = [o.strip() for o in self.CORS_ALLOWLIST.split(",") if o.strip()]

        # Production validation: no wildcards
        if self.ENV.lower() == "prod":
            if "*" in origins or not origins:
                raise ValueError(
                    "CORS_ALLOWLIST must be explicit in production (no wildcard). "
                    f"Current: {self.CORS_ALLOWLIST}"
                )

        return origins

    def get_allow_scopes(self) -> List[str]:
        """Parse ALLOW_SCOPES into list."""
        return [s.strip() for s in self.ALLOW_SCOPES.split() if s.strip()]

    def is_prod(self) -> bool:
        """Check if running in production."""
        return self.ENV.lower() == "prod"

    def is_dev(self) -> bool:
        """Check if running in development."""
        return self.ENV.lower() == "dev"


# Singleton instance
settings = Settings()


__all__ = ['Settings', 'settings']
