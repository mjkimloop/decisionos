from __future__ import annotations

from .base import ProviderV2


class OpenAIMockV2(ProviderV2):
    def estimate_cost(self, payload: dict) -> float:
        # naive: chars / 4 * unit
        text = str(payload.get("prompt", ""))
        return max(len(text) // 4, 1) * 0.0005

    def infer(self, payload: dict) -> dict:
        prompt = str(payload.get("prompt", ""))
        return {"result": f"mock:{prompt[:16]}", "meta": {"provider": "openai_mock_v2"}}

