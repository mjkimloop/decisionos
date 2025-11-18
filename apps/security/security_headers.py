from __future__ import annotations

import os
from ipaddress import ip_address, ip_network
from typing import List, Optional

from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=()",
    "X-Content-Type-Options": "nosniff",
}


def _parse_cidrs(raw: str) -> List:
    cidrs: List = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            cidrs.append(ip_network(token))
        except ValueError:
            continue
    return cidrs


class BaseSecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.enabled = os.getenv("DECISIONOS_SECURITY_HEADERS_ENABLE", "0") == "1"
        self.trusted_proxies = _parse_cidrs(os.getenv("DECISIONOS_TRUSTED_PROXY_CIDRS", ""))
        hosts_raw = os.getenv("DECISIONOS_ALLOWED_HOSTS", "")
        self.allowed_hosts = [host.strip().lower() for host in hosts_raw.split(",") if host.strip()]

    def _client_host(self, request) -> Optional[str]:
        client = request.client
        if client and client.host:
            return client.host
        return None

    def _is_trusted_proxy(self, host: Optional[str]) -> bool:
        if not host or not self.trusted_proxies:
            return False
        try:
            ip = ip_address(host)
        except ValueError:
            return False
        return any(ip in cidr for cidr in self.trusted_proxies)

    def _forwarded_for(self, request) -> Optional[str]:
        if not self._is_trusted_proxy(self._client_host(request)):
            return None
        header = request.headers.get("x-forwarded-for")
        if not header:
            return None
        return header.split(",")[0].strip()

    def _resolved_host(self, request) -> Optional[str]:
        host = None
        if self._is_trusted_proxy(self._client_host(request)):
            host = request.headers.get("x-forwarded-host")
        if not host:
            host = request.headers.get("host")
        return host.lower() if host else None

    async def dispatch(self, request, call_next):
        request.state.client_ip = self._forwarded_for(request) or self._client_host(request)
        resolved_host = self._resolved_host(request)
        if self.allowed_hosts and resolved_host:
            canonical = resolved_host.split(":")[0]
            if canonical not in self.allowed_hosts:
                raise HTTPException(status_code=400, detail="host_not_allowed")
        response = await call_next(request)
        if self.enabled:
            for header, value in SECURITY_HEADERS.items():
                response.headers.setdefault(header, value)
        return response
