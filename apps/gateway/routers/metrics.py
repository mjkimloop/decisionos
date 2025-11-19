from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from apps.metrics.registry import METRICS
from apps.policy.rbac_enforce import require_scopes

router = APIRouter(prefix="/api/v1", tags=["metrics"])


@router.get("/metrics", dependencies=[require_scopes("ops:read")])
async def metrics_json():
    snap = METRICS.snapshot()
    # 요약 필드 구성
    windows = snap.get("windows", {})
    p95 = 0.0
    err_rate = 0.0
    count = 0
    if windows:
        # 기본적으로 http_latency_ms에 대한 p95만 취함
        lat_keys = [k for k in windows if k.startswith("http_latency_ms")]
        if lat_keys:
            p95 = max(windows[k]["p95"] for k in lat_keys)
        err_keys = [k for k in windows if k.startswith("http_errors_total")]
        req_keys = [k for k in windows if k.startswith("http_requests_total")]
        err_sum = sum(windows[k]["sum"] for k in err_keys)
        req_sum = sum(windows[k]["sum"] for k in req_keys)
        if req_sum > 0:
            err_rate = err_sum / req_sum
        count = int(req_sum)
    return {
        "uptime_sec": snap.get("uptime_sec", 0),
        "p95_latency_ms": p95,
        "error_rate": err_rate,
        "count": count,
        "windows": windows,
    }


@router.get("/metrics/healthz")
async def metrics_healthz():
    # 간단히 에러율이 높으면 503 반환
    snap = METRICS.snapshot()
    windows = snap.get("windows", {})
    err_keys = [k for k in windows if k.startswith("http_errors_total")]
    req_keys = [k for k in windows if k.startswith("http_requests_total")]
    err_sum = sum(windows[k]["sum"] for k in err_keys)
    req_sum = sum(windows[k]["sum"] for k in req_keys)
    if req_sum > 0 and err_sum / req_sum > 0.2:
        return {"status": "degraded"}, 503
    return {"status": "ok"}


@router.get("/metrics/prometheus", dependencies=[require_scopes("ops:read")])
async def metrics_prometheus():
    text = METRICS.export_prom_text()
    return PlainTextResponse(text, media_type="text/plain; version=0.0.4")
