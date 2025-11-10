from __future__ import annotations

import base64
import json
import secrets
from dataclasses import dataclass
from typing import Dict


@dataclass
class OIDCProvider:
    issuer: str = "https://auth.decisionos.dev"
    client_id: str = "decisionos-cli"
    redirect_uri: str = "http://localhost:3000/callback"

    def build_authorize_url(self, state: str) -> str:
        return f"{self.issuer}/authorize?client_id={self.client_id}&redirect_uri={self.redirect_uri}&state={state}&response_type=code"

    def exchange_code(self, code: str, state: str) -> Dict[str, str]:
        # Stub: echo back a token derived from code
        token = base64.urlsafe_b64encode(f"{code}:{state}".encode("utf-8")).decode("utf-8")
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 3600,
        }

    def build_userinfo(self, token: str) -> Dict[str, str]:
        try:
            decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
            username = decoded.split(":", 1)[0]
        except Exception:
            username = "user"
        return {"sub": username, "email": f"{username}@example.com"}


provider_singleton = OIDCProvider()


def generate_state() -> str:
    return secrets.token_urlsafe(16)


def generate_code() -> str:
    return secrets.token_urlsafe(32)


__all__ = ["OIDCProvider", "provider_singleton", "generate_state", "generate_code"]

