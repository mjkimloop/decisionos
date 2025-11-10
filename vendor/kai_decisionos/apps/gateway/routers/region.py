from __future__ import annotations

from fastapi import APIRouter, Header

from apps.region.state import status, set_active

router = APIRouter(prefix="/api/v1/region", tags=["region"])


@router.get("/status")
def region_status():
    st = status()
    return {"active": st.active, "secondary": st.secondary, "from_config": st.from_config}


@router.post("/promote")
def region_promote(to: str, x_failover_token: str | None = Header(default=None, alias="X-Failover-Token")):
    # dev scaffold: token optional; production would verify secret/role
    st = set_active(to)
    return {"active": st.active}
