from __future__ import annotations

import asyncio
from typing import Dict, Any


class OpenAIAdapter:
    name = "openai"

    def estimate_cost(self, prompt: str, model: str) -> float:
        # Very rough mock: cost proportional to token count ~ len(prompt)/4
        tokens = max(len(prompt) // 4, 1)
        return tokens * 0.0005

    async def execute(self, prompt: str, model: str) -> Dict[str, Any]:
        # Mock behaviors by prompt prefix
        if prompt.startswith("FAIL"):
            raise RuntimeError("mock openai failure")
        if prompt.startswith("SLOW"):
            # Simulate slow response
            await asyncio.sleep(0.05)
        await asyncio.sleep(0)
        return {
            "content": f"openai:{prompt}",
            "meta": {"model": model, "adapter": self.name},
        }

