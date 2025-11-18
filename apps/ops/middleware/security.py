from __future__ import annotations

from apps.security.security_headers import BaseSecurityHeadersMiddleware


class OpsSecurityMiddleware(BaseSecurityHeadersMiddleware):
    """
    Adds standard security headers and basic host validation for Ops API.
    """

    pass


__all__ = ["OpsSecurityMiddleware"]
