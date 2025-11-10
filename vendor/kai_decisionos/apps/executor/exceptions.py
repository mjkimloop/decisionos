from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DomainError(Exception):
    message: str
    status_code: int = 400
    code: str | None = None

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.status_code}:{self.code or 'domain_error'}:{self.message}"

