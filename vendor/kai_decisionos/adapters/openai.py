import asyncio
from typing import Any, Dict
from .base import Adapter

class OpenAIAdapter(Adapter):
    """Adapter for a simulated OpenAI API call."""

    def __init__(self, delay: float = 0.1, should_fail: bool = False):
        self.delay = delay
        self.should_fail = should_fail

    def estimate_cost(self, prompt: str, model: str = "gpt-4") -> float:
        # Simplified cost estimation based on prompt length
        return len(prompt) * 0.0001

    async def execute(self, prompt: str, model: str = "gpt-4") -> Dict[str, Any]:
        await asyncio.sleep(self.delay)

        if self.should_fail:
            raise ConnectionError("Failed to connect to OpenAI API")

        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": f"This is a simulated response from {model}.",
                    }
                }
            ],
            "usage": {"total_tokens": len(prompt.split()) + 20},
            "meta": {"adapter": "openai"},
        }
