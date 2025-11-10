from __future__ import annotations

from apps.gateway import probes
from apps.region.state import status, set_active


def auto_failover(force: bool = False) -> dict:
    st = status()
    if force:
        ns = set_active(st.secondary or st.active)
        return {"switched": True, "active": ns.active}
    # readiness check
    ready = all(r.ok for r in probes.run_probes())
    if not ready and st.secondary and st.secondary != st.active:
        ns = set_active(st.secondary)
        return {"switched": True, "active": ns.active}
    return {"switched": False, "active": st.active}

