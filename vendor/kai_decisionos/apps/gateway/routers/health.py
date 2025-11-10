from __future__ import annotations

from fastapi import APIRouter

from apps.gateway import probes


router = APIRouter(prefix="/api/v1/health", tags=["health"]) 


@router.get("/live")
def live():
    return {"ok": True}


@router.get("/ready")
def ready():
    results = probes.run_probes()
    ok = all(r.ok for r in results)
    return {"ok": ok, "probes": [{"name": r.name, "ok": r.ok, "detail": r.detail} for r in results]}


@router.post("/degrade/on")
def degrade_on():
    probes.set_degrade(True)
    return {"ok": True}


@router.post("/degrade/off")
def degrade_off():
    probes.set_degrade(False)
    return {"ok": True}

