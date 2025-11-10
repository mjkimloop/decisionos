from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List

from .models import LineageEdge


class LineageStore:
    def __init__(self) -> None:
        self._edges: Dict[tuple[str, str, str | None, str | None], LineageEdge] = {}
        self._forward_index: Dict[str, set[tuple[str, str, str | None, str | None]]] = defaultdict(set)
        self._reverse_index: Dict[str, set[tuple[str, str, str | None, str | None]]] = defaultdict(set)

    def replace_outgoing(self, dataset: str, edges: Iterable[LineageEdge]) -> None:
        existing_keys = self._forward_index.get(dataset, set()).copy()
        for key in existing_keys:
            self._edges.pop(key, None)
            self._forward_index[dataset].discard(key)
            target = key[1]
            self._reverse_index[target].discard(key)
        for edge in edges:
            self._store_edge(edge)

    def _store_edge(self, edge: LineageEdge) -> None:
        key = edge.key()
        self._edges[key] = edge
        self._forward_index[edge.source_dataset].add(key)
        self._reverse_index[edge.target_dataset].add(key)

    def ingest(self, dataset: str, edges: Iterable[LineageEdge]) -> None:
        self.replace_outgoing(dataset, edges)

    def list_outgoing(self, dataset: str) -> List[LineageEdge]:
        return [self._edges[key] for key in sorted(self._forward_index.get(dataset, []))]

    def list_incoming(self, dataset: str) -> List[LineageEdge]:
        return [self._edges[key] for key in sorted(self._reverse_index.get(dataset, []))]


_STORE = LineageStore()


def ingest(dataset: str, edges: Iterable[LineageEdge]) -> None:
    edge_models = [edge if isinstance(edge, LineageEdge) else LineageEdge(**edge) for edge in edges]
    _STORE.ingest(dataset, edge_models)


def list_edges(dataset: str) -> List[LineageEdge]:
    return _STORE.list_outgoing(dataset)


def list_downstream(dataset: str) -> List[LineageEdge]:
    return _STORE.list_outgoing(dataset)


def list_upstream(dataset: str) -> List[LineageEdge]:
    return _STORE.list_incoming(dataset)


__all__ = [
    "ingest",
    "list_edges",
    "list_downstream",
    "list_upstream",
    "LineageStore",
]
