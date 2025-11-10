from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Set


@dataclass
class Edge:
    upstream: str
    downstream: str
    meta: dict


class LineageGraph:
    def __init__(self) -> None:
        self._downstream: Dict[str, Set[str]] = defaultdict(set)
        self._upstream: Dict[str, Set[str]] = defaultdict(set)
        self._meta: Dict[tuple[str, str], dict] = {}

    def add_edge(self, upstream: str, downstream: str, meta: dict | None = None) -> None:
        self._downstream[upstream].add(downstream)
        self._upstream[downstream].add(upstream)
        if meta:
            self._meta[(upstream, downstream)] = meta

    def edges(self) -> List[Edge]:
        return [Edge(u, d, self._meta.get((u, d), {})) for u in self._downstream for d in self._downstream[u]]

    def downstream(self, node: str, limit: int | None = None) -> List[str]:
        return self._bfs(node, self._downstream, limit)

    def upstream(self, node: str, limit: int | None = None) -> List[str]:
        return self._bfs(node, self._upstream, limit)

    def impact(self, node: str, limit: int | None = None) -> List[str]:
        return self.downstream(node, limit)

    @staticmethod
    def _bfs(start: str, adjacency: Dict[str, Set[str]], limit: int | None) -> List[str]:
        visited: Set[str] = set()
        queue: deque[str] = deque([start])
        result: List[str] = []
        while queue:
            current = queue.popleft()
            for neighbor in adjacency.get(current, set()):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                result.append(neighbor)
                queue.append(neighbor)
                if limit is not None and len(result) >= limit:
                    return result
        return result


graph = LineageGraph()


__all__ = ["graph", "LineageGraph", "Edge"]
