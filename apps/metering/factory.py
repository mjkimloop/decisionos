from __future__ import annotations
import os, json
from .store import InMemoryIdempoStore, SQLiteIdempoStore, IdempoStore

def build_idempo_store() -> IdempoStore:
    """
    우선순위:
    1) ENV DECISIONOS_METERING_STORE=json {"type":"sqlite","path":"..."} or {"type":"memory"}
    2) 기본: InMemory
    """
    spec = os.getenv("DECISIONOS_METERING_STORE")
    if spec:
        try:
            cfg = json.loads(spec)
            t = (cfg.get("type") or "memory").lower()
            if t == "sqlite":
                return SQLiteIdempoStore(cfg.get("path") or "var/metering/idempo.sqlite")
            return InMemoryIdempoStore()
        except Exception:
            return InMemoryIdempoStore()
    return InMemoryIdempoStore()
