from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Protocol, runtime_checkable, Any


@runtime_checkable
class Connector(Protocol):
    name: str

    def fetch(self, **kwargs) -> Any:  # pragma: no cover - interface definition
        ...


@dataclass
class RegisteredConnector:
    name: str
    loader: Callable[..., Connector]
    description: str = ""


class ConnectorRegistry:
    def __init__(self) -> None:
        self._registry: Dict[str, RegisteredConnector] = {}

    def register(self, name: str, loader: Callable[..., Connector], description: str = "") -> None:
        key = name.lower()
        self._registry[key] = RegisteredConnector(name=key, loader=loader, description=description)

    def create(self, name: str, **kwargs) -> Connector:
        key = name.lower()
        if key not in self._registry:
            raise KeyError(f"connector_not_found:{name}")
        return self._registry[key].loader(**kwargs)

    def list(self) -> Dict[str, str]:
        return {name: reg.description for name, reg in self._registry.items()}


registry = ConnectorRegistry()


def load_file(path: str | Path) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    return p.read_text(encoding="utf-8")


__all__ = ["Connector", "ConnectorRegistry", "registry", "RegisteredConnector", "load_file"]

