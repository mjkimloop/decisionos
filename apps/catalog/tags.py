from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

TAG_REGISTRY: Dict[str, dict] = {}


def tag_dataset(dataset_id: str, tags: dict) -> None:
    TAG_REGISTRY[dataset_id] = tags


def get_tags(dataset_id: str) -> dict:
    return TAG_REGISTRY.get(dataset_id, {})


__all__ = ["tag_dataset", "get_tags"]
