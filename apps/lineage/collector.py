from __future__ import annotations

from typing import Iterable, List

from .graph import graph, Edge


def ingest(edges: Iterable[dict]) -> int:
    count = 0
    for payload in edges:
        upstream = payload.get("upstream")
        downstream = payload.get("downstream")
        if not upstream or not downstream:
            continue
        meta = payload.get("meta", {})
        graph.add_edge(upstream, downstream, meta)
        count += 1
    return count


def list_edges() -> List[Edge]:
    return graph.edges()


__all__ = ["ingest", "list_edges"]
