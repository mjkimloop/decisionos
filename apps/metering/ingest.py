from __future__ import annotations
from typing import Iterable, Tuple, Optional
from .schema import MeterEvent
from .store import IdempoStore, InMemoryIdempoStore

def apply_event(ev: MeterEvent, store: IdempoStore) -> bool:
    k = ev.idempotency_key()
    if store.seen(k):
        return False
    return store.mark(k)

def filter_idempotent_with(store: IdempoStore, events: Iterable[MeterEvent]) -> Tuple[list[MeterEvent], int]:
    acc, dup = [], 0
    for ev in events:
        if apply_event(ev, store):
            acc.append(ev)
        else:
            dup += 1
    return acc, dup

# ✅ 기존 API 유지(기본은 InMemory)
def filter_idempotent(events: Iterable[MeterEvent]) -> Tuple[list[MeterEvent], int]:
    store = InMemoryIdempoStore()
    try:
        return filter_idempotent_with(store, events)
    finally:
        store.close()