from __future__ import annotations

from typing import Dict, Iterable


class SecretsVault:
    def __init__(self) -> None:
        self._store: Dict[str, str] = {}

    def register(self, name: str, value: str) -> None:
        self._store[name] = value

    def issue_scope(self, required: Iterable[str]) -> Dict[str, str]:
        scope = {}
        for secret_name in required:
            if secret_name not in self._store:
                raise KeyError(f"secret_not_found:{secret_name}")
            scope[secret_name] = self._store[secret_name]
        return scope


__all__ = ["SecretsVault"]
