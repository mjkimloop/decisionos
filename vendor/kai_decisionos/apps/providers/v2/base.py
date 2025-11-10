from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProviderV2(Protocol):
    def estimate_cost(self, payload: dict) -> float: ...
    def infer(self, payload: dict) -> dict: ...

