from __future__ import annotations

import os

from fastapi import HTTPException

from apps.security.security_headers import BaseSecurityHeadersMiddleware


class JudgeSecurityMiddleware(BaseSecurityHeadersMiddleware):
    """
    Extends the base header middleware with optional host allow-list enforcement.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        hosts_env = os.getenv("DECISIONOS_JUDGE_ALLOWED_HOSTS", "")
        self.judge_hosts = [h.strip().lower() for h in hosts_env.split(",") if h.strip()]

    async def dispatch(self, request, call_next):
        result = await super().dispatch(request, call_next)
        if self.judge_hosts:
            host = request.headers.get("host")
            if host:
                canonical = host.split(":")[0].lower()
                if canonical not in self.judge_hosts:
                    raise HTTPException(status_code=400, detail="judge_host_not_allowed")
        return result


__all__ = ["JudgeSecurityMiddleware"]
