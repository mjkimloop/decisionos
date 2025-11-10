from __future__ import annotations

import json
from typing import Dict


_STATIC_JWKS: Dict[str, object] = {
    "keys": [
        {
            "kty": "RSA",
            "kid": "demo",
            "use": "sig",
            "n": "oahUI...demo",
            "e": "AQAB",
        }
    ]
}


def get_jwks() -> Dict[str, object]:
    return _STATIC_JWKS


__all__ = ["get_jwks"]

