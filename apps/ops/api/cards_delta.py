from __future__ import annotations
from fastapi import APIRouter, Response, Header
from typing import Optional
import json, os, time, pathlib

from apps.ops.cache.snapshot_store import build_snapshot_store
from apps.ops.cache.delta import compute_etag, make_delta_etag, not_modified

router = APIRouter()

TTL = int(os.getenv("DECISIONOS_CARDS_TTL", "60"))
INDEX_PATH = os.getenv("DECISIONOS_EVIDENCE_INDEX", "var/evidence/index.json")
TENANT = os.getenv("DECISIONOS_TENANT", "").strip()
_KEY_BASE = "cards:reason-trends"
KEY = f"{TENANT}:{_KEY_BASE}" if TENANT else _KEY_BASE

# In-memory cache for last ETag (per-route)
_LAST_ETAG_CACHE = {}

def _load_live_payload() -> dict:
    p = pathlib.Path(INDEX_PATH)
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            # 최소 필드만 정규화 (대시보드가 기대하는 키)
            trends = data.get("reason_trends") or data.get("trends") or []
            top = data.get("top_impact") or []
            gen_at = data.get("generated_at") or int(pathlib.Path(INDEX_PATH).stat().st_mtime)
            return {
                "generated_at": gen_at,
                "reason_trends": trends,
                "top_impact": top,
            }
        except Exception:
            pass
    # 인덱스가 없을 때의 안전한 기본값
    return {"generated_at": int(time.time()), "reason_trends": [], "top_impact": []}

@router.get("/reason-trends")
async def get_reason_trends(
    response: Response,
    if_none_match: Optional[str] = Header(default=None),
):
    store = build_snapshot_store()
    route_key = KEY

    # Get previous ETag from cache
    prev_etag = _LAST_ETAG_CACHE.get(route_key)

    # If-None-Match short-circuit using last etag
    if if_none_match and prev_etag and if_none_match == prev_etag:
        response.status_code = 304
        response.headers["ETag"] = prev_etag
        response.headers["Cache-Control"] = f"public, max-age={TTL}"
        return

    payload = _load_live_payload()
    # 기본 ETag는 payload 해시, 이전 etag는 delta 계산 용도로만 사용
    server_etag = compute_etag(payload)

    client_tag = if_none_match.strip('"') if if_none_match else None
    if client_tag == server_etag:
        response.status_code = 304
        response.headers["ETag"] = server_etag
        response.headers["Cache-Control"] = f"public, max-age={TTL}"
        return

    # 스냅샷 갱신 (etag를 키로 사용)
    await store.set(server_etag, payload, ttl_sec=TTL)

    # Update ETag cache
    _LAST_ETAG_CACHE[route_key] = server_etag

    response.headers["ETag"] = server_etag
    response.headers["Cache-Control"] = f"public, max-age={TTL}"
    return payload
