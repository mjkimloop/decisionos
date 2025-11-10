from __future__ import annotations

from collections import deque
from typing import Dict, List, Set, Tuple

from .collector import list_downstream, list_upstream
from .models import LineageEdge


def _dump_edges(edges: List[LineageEdge]) -> List[dict]:
    return [edge.model_dump(mode="json") for edge in edges]


def graph(dataset: str, depth: int = 1) -> dict:
    if depth < 0:
        raise ValueError("depth_must_be_positive")
    nodes: Set[str] = {dataset}
    forward_edges: List[LineageEdge] = []
    reverse_edges: List[LineageEdge] = []

    forward_queue: deque[Tuple[str, int]] = deque([(dataset, 0)])
    visited_forward: Dict[str, int] = {dataset: 0}
    while forward_queue:
        current, level = forward_queue.popleft()
        if level >= depth:
            continue
        for edge in list_downstream(current):
            forward_edges.append(edge)
            target = edge.target_dataset
            nodes.add(target)
            if visited_forward.get(target, depth + 1) > level + 1:
                visited_forward[target] = level + 1
                forward_queue.append((target, level + 1))

    reverse_queue: deque[Tuple[str, int]] = deque([(dataset, 0)])
    visited_reverse: Dict[str, int] = {dataset: 0}
    while reverse_queue:
        current, level = reverse_queue.popleft()
        if level >= depth:
            continue
        for edge in list_upstream(current):
            reverse_edges.append(edge)
            source = edge.source_dataset
            nodes.add(source)
            if visited_reverse.get(source, depth + 1) > level + 1:
                visited_reverse[source] = level + 1
                reverse_queue.append((source, level + 1))

    return {
        "root": dataset,
        "depth": depth,
        "nodes": sorted(nodes),
        "forward": _dump_edges(forward_edges),
        "upstream": _dump_edges(reverse_edges),
    }


def impact(dataset: str, field: str | None = None, depth: int = 3) -> dict:
    if depth < 0:
        raise ValueError("depth_must_be_positive")
    impacted = []
    queue: deque[tuple[str, str | None, int]] = deque([(dataset, field, 0)])
    seen: Set[tuple[str, str | None]] = set()
    while queue:
        current_dataset, current_field, level = queue.popleft()
        if level >= depth:
            continue
        for edge in list_downstream(current_dataset):
            if current_field and edge.source_field and edge.source_field != current_field:
                continue
            key = (edge.target_dataset, edge.target_field)
            if key in seen:
                continue
            seen.add(key)
            impacted.append(
                {
                    "dataset": edge.target_dataset,
                    "field": edge.target_field,
                    "level": level + 1,
                    "transformation": edge.transformation,
                    "confidence": edge.confidence,
                }
            )
            queue.append((edge.target_dataset, edge.target_field, level + 1))
    return {
        "root": dataset,
        "field": field,
        "depth": depth,
        "impacted": impacted,
    }


__all__ = ["graph", "impact"]
