# apps/gateway/security/cors.py
"""
CORS middleware with strict allowlist enforcement.

Security (v0.5.11u-5):
- Production: explicit allowlist required, wildcard (*) forbidden
- Development: defaults to localhost origins
- Validates environment configuration at boot time
"""
from __future__ import annotations
import os
import re
import logging
from typing import List
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

log = logging.getLogger(__name__)


def _parse_allowlist(raw: str) -> List[str]:
    """Parse CORS allowlist from comma/space-separated string."""
    parts = [p.strip() for p in re.split(r"[,\s]+", raw or "") if p.strip()]
    return parts


def attach_strict_cors(app: FastAPI) -> None:
    """
    Attach CORS middleware with strict allowlist enforcement.

    Environment variables:
    - DECISIONOS_ENV: Environment (dev/staging/prod)
    - DECISIONOS_CORS_ALLOWLIST: Comma-separated allowed origins

    Security:
    - Production: allowlist must be explicit (no wildcard)
    - Development: defaults to localhost:3000, 127.0.0.1:3000
    - Raises RuntimeError if production allowlist is missing or wildcard

    Example:
        DECISIONOS_CORS_ALLOWLIST=https://app.example.com,https://console.example.com
    """
    env = os.getenv("DECISIONOS_ENV", "dev").lower()
    allow_raw = os.getenv("DECISIONOS_CORS_ALLOWLIST", "")
    origins = _parse_allowlist(allow_raw)

    # Production safety check
    if env == "prod":
        if not origins or allow_raw.strip() == "*" or origins == ["*"]:
            raise RuntimeError(
                "FATAL: CORS allowlist must be explicit in production (no wildcard). "
                "Set DECISIONOS_CORS_ALLOWLIST to comma-separated origins. "
                f"Current value: '{allow_raw}'"
            )
        log.info("cors_prod_allowlist", extra={"origins": origins, "count": len(origins)})
    elif not origins:
        # Development default: localhost only
        origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
        log.info("cors_dev_default", extra={"origins": origins})
    else:
        log.info("cors_allowlist", extra={"env": env, "origins": origins})

    # Attach middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=[
            "ETag",
            "X-Delta-Base-ETag",
            "X-Delta-Accepted",
            "X-Delta-Probe",
            "X-RBAC-Map-ETag",
        ],
        max_age=600,
    )

    log.info(
        "cors_attached",
        extra={
            "env": env,
            "origins": origins,
            "allow_credentials": True,
            "max_age": 600,
        },
    )
