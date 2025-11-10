from __future__ import annotations

import secrets
from typing import Dict

_TOKEN_MAP: Dict[str, str] = {}


def tokenize(value: str) -> str:
    token = secrets.token_hex(len(value))[: len(value)]
    _TOKEN_MAP[token] = value
    return token


def detokenize(token: str) -> str:
    if token not in _TOKEN_MAP:
        raise KeyError("token_not_found")
    return _TOKEN_MAP[token]


__all__ = ["tokenize", "detokenize"]
