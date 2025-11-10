from __future__ import annotations

import abc
from typing import Any, Dict


class JudgeProvider(abc.ABC):
    """Abstract provider interface."""

    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id

    @abc.abstractmethod
    async def evaluate(self, evidence: Dict[str, Any], slo: Dict[str, Any]) -> Dict[str, Any]:
        """Return dict with decision/reasons/meta."""


__all__ = ["JudgeProvider"]
