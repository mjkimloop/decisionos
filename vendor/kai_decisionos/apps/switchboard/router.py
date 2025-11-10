from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import random

from .adapters import Adapter
from .adapters.local import LocalAdapter
from .adapters.openai import OpenAIAdapter


@dataclass
class Router:
    adapters: Dict[str, Adapter] = field(default_factory=lambda: {
        "local": LocalAdapter(),
        "openai": OpenAIAdapter(),
    })
    capability_map: Dict[str, str] = field(default_factory=lambda: {
        "default": "openai",
        "creative_writing": "openai",
        "batch": "local",
    })
    default_adapter: str = "local"

    def _select_primary(self, capability: str) -> str:
        return self.capability_map.get(capability, self.capability_map.get("default", self.default_adapter))

    async def route(
        self,
        prompt: str,
        capability: str = "default",
        cost_budget: Optional[float] = 0.5,
        timeout: float = 1.0,
        canary_percent: float = 0.0,
        chaos: bool = False,
    ) -> Dict[str, Any]:
        budget_cost = max((cost_budget or 0.0), 0.0)
        primary_name = self._select_primary(capability)
        primary = self.adapters.get(primary_name, self.adapters[self.default_adapter])
        fallback = self.adapters[self.default_adapter]

        # Cost-based fallback decision
        est_cost = float(primary.estimate_cost(prompt, primary_name))
        adapter_to_use = primary if est_cost <= budget_cost else fallback
        fallback_reason = "cost" if adapter_to_use is fallback and primary is not fallback else None

        try:
            # chaos injection (scaffold)
            if chaos:
                raise RuntimeError("chaos: forced error")
            result = await asyncio.wait_for(adapter_to_use.execute(prompt, primary_name), timeout=timeout)
            meta = {
                "adapter_used": adapter_to_use.__class__.__name__.replace("Adapter", "").lower(),
                "primary": primary_name,
                "fallback_reason": fallback_reason,
                "estimated_cost": est_cost,
                "capability": capability,
                "budget": {"cost": budget_cost, "timeout": timeout},
            }
            # canary shadow (meta only, no second call in scaffold)
            if canary_percent and canary_percent >= 1.0:
                meta["canary"] = True
            elif canary_percent and random.random() < max(0.0, min(1.0, canary_percent)):
                meta["canary"] = True
            result.setdefault("meta", {}).update(meta)
            return result
        except asyncio.TimeoutError:
            # Timeout fallback to local
            res = await fallback.execute(prompt, self.default_adapter)
            res.setdefault("meta", {}).update({
                "adapter_used": fallback.__class__.__name__.replace("Adapter", "").lower(),
                "primary": primary_name,
                "fallback_reason": "timeout",
                "estimated_cost": est_cost,
                "capability": capability,
                "budget": {"cost": budget_cost, "timeout": timeout},
            })
            return res
        except Exception:
            # Error fallback to local
            res = await fallback.execute(prompt, self.default_adapter)
            res.setdefault("meta", {}).update({
                "adapter_used": fallback.__class__.__name__.replace("Adapter", "").lower(),
                "primary": primary_name,
                "fallback_reason": "error",
                "estimated_cost": est_cost,
                "capability": capability,
                "budget": {"cost": budget_cost, "timeout": timeout},
            })
            return res
