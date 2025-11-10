from __future__ import annotations

from typing import Dict, Iterable

from .types import AdapterResult, IPayAdapter

_REGISTRY: Dict[str, IPayAdapter] = {}


def register_adapter(name: str, adapter: IPayAdapter) -> None:
    _REGISTRY[name] = adapter


def get_adapter(name: str) -> IPayAdapter:
    if name not in _REGISTRY:
        raise ValueError(f"unknown_adapter:{name}")
    return _REGISTRY[name]


def list_adapters() -> Iterable[str]:
    return _REGISTRY.keys()


__all__ = ["register_adapter", "get_adapter", "list_adapters", "AdapterResult", "IPayAdapter"]
