from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Artifact:
    name: str
    version: str
    channel: str
    path: str
    metadata: dict


class OCIRegistry:
    def __init__(self) -> None:
        self._artifacts: Dict[str, Artifact] = {}

    def push(self, ref: str, artifact: Artifact) -> None:
        self._artifacts[ref] = artifact

    def get(self, ref: str) -> Artifact:
        if ref not in self._artifacts:
            raise KeyError("artifact_not_found")
        return self._artifacts[ref]

    def list_channel(self, channel: str) -> List[Artifact]:
        return [artifact for artifact in self._artifacts.values() if artifact.channel == channel]


REGISTRY = OCIRegistry()

__all__ = ["Artifact", "OCIRegistry", "REGISTRY"]
