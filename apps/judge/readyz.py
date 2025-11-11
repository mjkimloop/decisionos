from __future__ import annotations
from typing import Dict, Tuple, List, Any, Optional
import os, time
from datetime import datetime, timezone

DEFAULT_SKEW_SEC = int(os.getenv("DECISIONOS_CLOCK_SKEW_MAX", "10"))
KEY_GRACE_SEC = int(os.getenv("DECISIONOS_KEY_GRACE_SEC", "300"))

def check_ready(key_loader: Any = None, replay_store: Optional[Any] = None) -> Tuple[bool, Dict]:
    reasons: List[str] = []

    # 1) Keyset freshness
    if key_loader:
        try:
            # MultiKeyLoader has keys() method
            keys = key_loader.keys()
            if not keys:
                reasons.append("keys.missing")
        except Exception as e:
            reasons.append(f"keys.load_failed:{str(e)[:50]}")

    # 2) Replay store ping
    backend = os.getenv("DECISIONOS_REPLAY_BACKEND", "sqlite")
    if replay_store:
        try:
            if hasattr(replay_store, "ping"):
                replay_store.ping()
        except Exception as e:
            reasons.append(f"replay.unreachable:{str(e)[:50]}")

    # 3) Clock skew config
    max_skew = DEFAULT_SKEW_SEC
    if max_skew <= 0:
        reasons.append("clock.skew_config_invalid")

    ok = (len(reasons) == 0)
    return ok, {"backend": backend, "reasons": reasons, "skew_max": max_skew}
