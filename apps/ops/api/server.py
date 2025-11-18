from __future__ import annotations

import os
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import Dict, List

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from apps.ops.api.cache import cache, compute_etag_for_html, compute_etag_for_json
from apps.ops.api.cards_delta import router as cards_delta_router
from apps.ops.reports.reason_trend import aggregate_reason_trend, get_index_signature
from apps.policy import pep

EVIDENCE_ROOT = os.getenv("DECISIONOS_EVIDENCE_ROOT", "var/evidence")


def _cors_origins() -> List[str]:
    raw = os.getenv("DECISIONOS_CORS_ORIGINS", "")
    return [entry.strip() for entry in raw.split(",") if entry.strip()]


def _ttl_sec() -> int:
    val = os.getenv("DECISIONOS_OPS_CACHE_TTL_SEC", "60")
    try:
        ttl = int(val)
    except Exception:
        ttl = 60
    return max(1, ttl)


def _httpdate(iso_ts: str | None) -> str | None:
    if not iso_ts:
        return None
    try:
        iso_val = iso_ts.replace("Z", "+00:00")
        stamp = datetime.fromisoformat(iso_val)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return format_datetime(stamp)


def _cache_headers(etag: str, ttl: int, last_modified: str | None) -> Dict[str, str]:
    headers = {
        "ETag": etag,
        "Cache-Control": f"public, max-age={ttl}",
        "Surrogate-Control": f"public, max-age={ttl}",
        "Vary": "Accept, If-None-Match",
    }
    http_date = _httpdate(last_modified)
    if http_date:
        headers["Last-Modified"] = http_date
    return headers


app = FastAPI(title="DecisionOS Ops API", version="v0.5.11p-1")
app.include_router(cards_delta_router)

try:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins() or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
except Exception:
    pass


def rbac_ops_read() -> None:
    try:
        pep.require("ops:read")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _cache_key(prefix: str, *parts: str) -> str:
    suffix = ":".join(part or "null" for part in parts)
    return f"{prefix}:{suffix}"


def _handle_cache_hit(entry, ttl: int, last_modified_hint: str | None, if_none_match: str | None) -> Response | None:
    if not entry:
        return None
    headers = _cache_headers(entry.etag, ttl, entry.last_modified or last_modified_hint)
    if if_none_match and if_none_match == entry.etag:
        return Response(status_code=304, headers=headers)
    payload = entry.payload
    if isinstance(payload, str):
        return HTMLResponse(payload, headers=headers)
    return JSONResponse(payload, headers=headers)


@app.get("/healthz")
def healthz() -> JSONResponse:
    return JSONResponse({"ok": True, "version": "v0.5.11p-1"})


@app.get("/ops/reason-trend", dependencies=[Depends(rbac_ops_read)])
def reason_trend(
    if_none_match: str | None = Header(default=None),
    days: int = Query(7, ge=1, le=90),
) -> Response:
    ttl = _ttl_sec()
    index_sig, index_last_updated = get_index_signature(EVIDENCE_ROOT)
    key = _cache_key("trend", str(days), index_sig)
    entry = cache.peek(key)
    cached = _handle_cache_hit(entry, ttl, index_last_updated, if_none_match)
    if cached:
        return cached

    trend = aggregate_reason_trend(EVIDENCE_ROOT, days)
    etag, _ = compute_etag_for_json(trend)
    last_modified_value = trend.get("last_updated") or index_last_updated or trend.get("generated_at")
    entry = cache.put(key, etag, trend, ttl, last_modified_value)
    return JSONResponse(trend, headers=_cache_headers(entry.etag, ttl, entry.last_modified))


@app.get("/ops/reason-trend/card", dependencies=[Depends(rbac_ops_read)])
def reason_trend_card(
    if_none_match: str | None = Header(default=None),
    days: int = Query(7, ge=1, le=90),
    topK: int = Query(5, ge=1, le=20),
) -> Response:
    ttl = _ttl_sec()
    index_sig, index_last_updated = get_index_signature(EVIDENCE_ROOT)
    key = _cache_key("trend_card", str(days), str(topK), index_sig)
    entry = cache.peek(key)
    cached = _handle_cache_hit(entry, ttl, index_last_updated, if_none_match)
    if cached:
        return cached

    trend = aggregate_reason_trend(EVIDENCE_ROOT, days)
    top = (trend.get("total_top") or [])[:topK]
    payload = {
        "window_days": trend.get("window_days"),
        "generated_at": trend.get("generated_at"),
        "top": top,
        "count_evidence": trend.get("count_evidence"),
        "last_updated": trend.get("last_updated"),
    }
    etag, _ = compute_etag_for_json(payload)
    last_modified_value = payload.get("last_updated") or index_last_updated or trend.get("generated_at")
    entry = cache.put(key, etag, payload, ttl, last_modified_value)
    return JSONResponse(payload, headers=_cache_headers(entry.etag, ttl, entry.last_modified))


@app.get("/ops/reason-trend/card.html", response_class=HTMLResponse, dependencies=[Depends(rbac_ops_read)])
def reason_trend_card_html(
    if_none_match: str | None = Header(default=None),
    days: int = Query(7, ge=1, le=90),
    topK: int = Query(5, ge=1, le=20),
) -> Response:
    ttl = _ttl_sec()
    index_sig, index_last_updated = get_index_signature(EVIDENCE_ROOT)
    key = _cache_key("trend_card_html", str(days), str(topK), index_sig)
    entry = cache.peek(key)
    cached = _handle_cache_hit(entry, ttl, index_last_updated, if_none_match)
    if cached:
        return cached

    trend = aggregate_reason_trend(EVIDENCE_ROOT, days)
    top = (trend.get("total_top") or [])[:topK]
    list_items = "".join(f"<li><code>{code}</code> x {count}</li>" for code, count in top)
    html = (
        "<html>"
        "<head><meta charset=\"utf-8\" /><title>Reason Trend</title></head>"
        "<body>"
        f"<h3>Reason Trend (last {trend.get('window_days')} days)</h3>"
        f"<p>generated_at: {trend.get('generated_at')}</p>"
        f"<p>total reason count: {trend.get('count_evidence')}</p>"
        f"<ul>{list_items}</ul>"
        "</body></html>"
    )
    etag, _ = compute_etag_for_html(html)
    last_modified_value = trend.get("last_updated") or index_last_updated or trend.get("generated_at")
    entry = cache.put(key, etag, html, ttl, last_modified_value)
    headers = _cache_headers(entry.etag, ttl, entry.last_modified)
    return HTMLResponse(html, headers=headers)


@app.get("/metrics")
def metrics() -> Response:
    """간단한 텍스트 기반 메트릭 노출 (필요 시 Prometheus 서식)."""
    lines = []
    try:
        from apps.ops.api import cards_delta

        lines.append(f'decisionos_cards_etag_total{{result="hit"}} {_safe_int(cards_delta._COUNTERS.get("cards_304", 0))}')
        lines.append(f'decisionos_cards_etag_total{{result="miss"}} {_safe_int(cards_delta._COUNTERS.get("cards_200", 0))}')
    except Exception:
        lines.append('decisionos_cards_etag_total{result="hit"} 0')
        lines.append('decisionos_cards_etag_total{result="miss"} 0')
    body = "\n".join(lines) + "\n"
    return PlainTextResponse(body, media_type="text/plain")


def _safe_int(val) -> int:
    try:
        return int(val)
    except Exception:
        return 0
