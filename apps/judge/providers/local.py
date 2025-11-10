from __future__ import annotations

import asyncio
import time
from typing import Any, Dict

from .base import JudgeProvider
from apps.judge import slo_judge


class LocalJudgeProvider(JudgeProvider):
    def __init__(self, provider_id: str = "local") -> None:
        super().__init__(provider_id)

    async def evaluate(self, evidence: Dict[str, Any], slo: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()

        def _run():
            decision, reasons = slo_judge.evaluate(evidence, slo)
            return {"decision": decision, "reasons": reasons}

        result = await asyncio.to_thread(_run)
        latency_ms = (time.perf_counter() - start) * 1000
        result.setdefault("meta", {})["latency_ms"] = round(latency_ms, 2)
        result["id"] = self.provider_id
        return result


__all__ = ["LocalJudgeProvider"]
