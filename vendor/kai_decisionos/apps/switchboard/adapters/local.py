from __future__ import annotations

import asyncio
from typing import Dict, Any


class LocalAdapter:
    name = "local"

    def estimate_cost(self, prompt: str, model: str) -> float:
        # Local execution assumed near-zero marginal cost
        return 0.0

    async def execute(self, prompt: str, model: str) -> Dict[str, Any]:
        # Simulate minimal processing delay
        await asyncio.sleep(0)
        return {
            "content": f"local:{prompt}",
            "meta": {"model": model, "adapter": self.name},
        }

