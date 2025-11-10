from __future__ import annotations

from typing import Protocol, Dict, Any


class Adapter(Protocol):
    name: str

    def estimate_cost(self, prompt: str, model: str) -> float:
        ...

    async def execute(self, prompt: str, model: str) -> Dict[str, Any]:
        ...

