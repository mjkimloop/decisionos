from typing import Any, Dict
from .base import Adapter

class LocalAdapter(Adapter):
    """Adapter for a fast, free, local model."""

    def estimate_cost(self, prompt: str, model: str = "local-model") -> float:
        return 0.0

    async def execute(self, prompt: str, model: str = "local-model") -> Dict[str, Any]:
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "This is a simulated response from the local model.",
                    }
                }
            ],
            "usage": {"total_tokens": len(prompt.split())},
            "meta": {"adapter": "local"},
        }
