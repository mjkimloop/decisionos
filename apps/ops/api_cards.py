from fastapi import APIRouter, Depends, HTTPException, Header, Response, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from base64 import urlsafe_b64encode, urlsafe_b64decode
import os, json

router = APIRouter()

# ETag 스냅샷 저장소 (프로세스 단일톤)
from .cache.etag_store import build_etag_store
_ETAG_STORE = build_etag_store()

# Mock RBAC for now - will integrate with existing RBAC system
def require_scope(scope: str):
    def dependency():
        # In production, this would validate RBAC token
        return True
    return dependency

class AggregateReq(BaseModel):
    reasons: List[str] = Field(default_factory=list)
    top: int = 5

@router.get("/cards/reason-trends/palette")
def get_palette(_=Depends(require_scope("ops:read"))):
    from .cards.aggregation import palette_with_desc, etag_seed
    return {"seed": etag_seed(), "palette": palette_with_desc()}

@router.post("/cards/reason-trends")
def post_trends(req: AggregateReq, _=Depends(require_scope("ops:read"))):
    from .cards.aggregation import palette_with_desc, aggregate_reasons, label_catalog_hash
    if req.top < 1 or req.top > 50:
        raise HTTPException(status_code=400, detail="top must be 1..50")
    agg = aggregate_reasons(req.reasons, top=req.top)
    return {
        "catalog_sha": label_catalog_hash(),
        "palette": palette_with_desc(),
        **agg
    }

def _parse_iso(s: str) -> datetime:
    if s.endswith("Z"):
        return datetime.fromisoformat(s.replace("Z","+00:00"))
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

def _encode_cont_token(bucket_size: str, last_end_iso: str) -> str:
    obj = {"bucket_size": bucket_size, "last_end": last_end_iso}
    return urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode("utf-8")).decode("ascii")

def _decode_cont_token(token: str) -> dict | None:
    try:
        obj = json.loads(urlsafe_b64decode(token.encode("ascii")).decode("utf-8"))
        if not isinstance(obj, dict):
            return None
        return obj
    except Exception:
        return None

@router.get("/cards/reason-trends/summary")
def get_summary(
    request: Request,
    response: Response,
    start: str,
    end: str,
    top: int = 5,
    bucket: Optional[str] = None,
    seasonality: str = "off",
    delta: str = "off",
    bucket_limit: int = 24,
    top_buckets: int = 3,
    if_none_match: Optional[str] = Header(default=None, alias="If-None-Match"),
    if_delta_token: Optional[str] = Header(default=None, alias="X-If-Delta-Token"),
    delta_require_same_window: bool = False,
    delta_base_etag: Optional[str] = Header(default=None, alias="X-Delta-Base-ETag"),
    cont_token: Optional[str] = Header(default=None, alias="X-Bucket-Continuity-Token"),
    _=Depends(require_scope("ops:read")),
):
    from .cards.aggregation import (
        palette_with_desc, aggregate_reasons, label_catalog_hash,
        make_snapshot_payload, snapshot_etag, snapshot_token, try_decode_token, diff_counts
    )
    from .cards.events import load_reason_events
    from .cards.etag_v2 import build_cards_etag_key, compute_cards_etag
    from .cards.delta import compute_delta_summary, same_window

    if top < 1 or top > 50:
        raise HTTPException(status_code=400, detail="top must be 1..50")
    try:
        dt_start, dt_end = _parse_iso(start), _parse_iso(end)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid start/end")
    if not (dt_end > dt_start):
        raise HTTPException(status_code=400, detail="end must be after start")

    ev_path = os.environ.get("REASON_EVENTS_PATH", "var/evidence/reasons.jsonl")
    reasons = load_reason_events(dt_start, dt_end, ev_path)
    agg = aggregate_reasons(reasons, top=top)
    window = {"start": dt_start.isoformat(), "end": dt_end.isoformat()}

    # ETag v2: comprehensive cache key
    label_cat_path = os.environ.get("LABEL_CATALOG_PATH", "configs/ops/label_catalog.json")
    group_weights_path = os.environ.get("GROUP_WEIGHTS_PATH", "configs/ops/group_weights.json")
    seasonal_path = os.environ.get("SEASONAL_THRESHOLDS_PATH", "configs/ops/seasonal_thresholds.json")
    data_rev = os.environ.get("CARDS_DATA_REV", "")

    etag_key = build_cards_etag_key(
        start, end,
        bucket=bucket or "none",
        seasonality=seasonality,
        delta_enabled=(delta == "on" or bool(if_delta_token)),
        delta_require_same_window=delta_require_same_window,
        continuity_token=cont_token,
        label_catalog_path=label_cat_path,
        group_weights_path=group_weights_path,
        seasonal_thresholds_path=seasonal_path,
        data_revision_token=data_rev
    )
    current_etag = compute_cards_etag(etag_key)

    # 304 처리 (If-None-Match 우선: delta 무시)
    if if_none_match and if_none_match == current_etag:
        response.status_code = 304
        return None

    # Legacy payload for delta token (backwards compat)
    payload = make_snapshot_payload(window, agg["raw"], label_catalog_hash())

    # Delta 처리
    delta = None
    if if_delta_token:
        prev = try_decode_token(if_delta_token)
        if prev and isinstance(prev.get("raw"), dict):
            delta = diff_counts(prev["raw"], agg["raw"])

    # 버킷 분포 (+ 연속 토큰 페이지네이션)
    buckets = None
    buckets_scored = None
    top_list = None
    cont_out = None
    has_more = False

    if bucket:
        from .cards.bucketing import bucketize_counts_by_time, apply_bucket_scores, pick_top_buckets
        from .cards.grouping import group_of, load_group_weights

        if bucket not in ("hour", "day"):
            raise HTTPException(status_code=400, detail="bucket must be 'hour' or 'day'")
        if bucket_limit < 1 or bucket_limit > 1000:
            raise HTTPException(status_code=400, detail="bucket_limit must be 1..1000")

        # Load rows with ts + reason
        rows = []
        from .cards.events import load_reason_events
        ev_path2 = os.environ.get("REASON_EVENTS_PATH", "var/evidence/reasons.jsonl")
        if os.path.exists(ev_path2):
            with open(ev_path2, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    obj = json.loads(line)
                    ts_str = obj.get("ts", "")
                    reason = obj.get("reason", "")
                    if ts_str and reason:
                        # Parse and filter by window
                        try:
                            ts = _parse_iso(ts_str)
                            if ts >= dt_start and ts < dt_end:
                                rows.append({"ts": ts_str, "reason": reason})
                        except Exception:
                            pass

        all_buckets = bucketize_counts_by_time(rows, bucket)

        # continuity offset
        offset_idx = 0
        if cont_token:
            prev = _decode_cont_token(cont_token)
            if prev and prev.get("bucket_size") == bucket and "last_end" in prev:
                last_end = _parse_iso(prev["last_end"])
                # 현재 윈도 내에서 last_end 이후 버킷부터
                for i, b in enumerate(all_buckets):
                    if _parse_iso(b["end"]) > last_end:
                        offset_idx = i
                        break
                else:
                    offset_idx = len(all_buckets)

        page = all_buckets[offset_idx:offset_idx + bucket_limit]
        buckets = page

        # 다음 페이지 토큰
        has_more = (offset_idx + bucket_limit) < len(all_buckets)
        if page:
            last_end_iso = page[-1]["end"]
            cont_out = _encode_cont_token(bucket, last_end_iso)
            response.headers["X-Bucket-Continuity-Token"] = cont_out
        response.headers["X-Bucket-Has-More"] = "1" if has_more else "0"

        # 가중 점수 & 상위 N 버킷
        if buckets:
            weights = load_group_weights()
            buckets_scored = apply_bucket_scores(buckets, group_of, weights)
            if top_buckets and top_buckets > 0:
                top_list = pick_top_buckets(buckets_scored, top_buckets)

    # 상한선 추가 (v0.5.11r-9)
    from .cards.thresholds import load_slo_thresholds
    thresholds = load_slo_thresholds()

    # 전체 요약 body 구성
    full_summary = {
        "catalog_sha": payload["catalog_sha"],
        "window": window,
        "palette": palette_with_desc(),
        **agg,
        "buckets": buckets_scored if buckets_scored is not None else buckets,
        "top_buckets": top_list,
        "delta": delta,
        "delta_token": snapshot_token(payload),
        "continuity": {
            "bucket_size": bucket,
            "token": cont_out,
            "has_more": has_more,
            "limit": bucket_limit,
        } if bucket else None,
        "thresholds": thresholds if thresholds else None,
    }

    # ETag 스냅샷 저장
    _ETAG_STORE.put(current_etag, full_summary, ttl_sec=86400)

    # Delta 모드 처리
    delta_applied = False
    body = full_summary

    if delta == "on" and delta_base_etag:
        prev_snapshot = _ETAG_STORE.get(delta_base_etag)
        if prev_snapshot is not None:
            # 윈도 일치성 체크 (옵션)
            if not delta_require_same_window or same_window(prev_snapshot, full_summary):
                body = compute_delta_summary(prev_snapshot, full_summary)
                delta_applied = True

    # 응답 헤더 설정
    response.headers["ETag"] = current_etag
    response.headers["Cache-Control"] = "public, max-age=60"
    response.headers["X-ETag-Keys"] = "period,bucket,seasonality,delta,continuity,hashes"
    if delta_base_etag:
        response.headers["X-Delta-Base-ETag"] = delta_base_etag
    response.headers["X-Delta-New-ETag"] = current_etag
    response.headers["X-Delta-Applied"] = "true" if delta_applied else "false"

    return body

@router.get("/cards/label-heatmap")
def label_heatmap(
    period: str,
    bucket: str = "day",
    group_axis: str = "group",
    label_axis: str = "label",
    if_none_match: Optional[str] = Header(default=None, alias="If-None-Match"),
    _=Depends(require_scope("ops:read"))
):
    """라벨 히트맵 카드: period/bucket별 그룹·라벨 빈도 매트릭스"""
    import hashlib
    # 예: var/evidence/index/summary.json ← 인덱서 산출물
    path = os.getenv("DECISIONOS_EVIDENCE_INDEX", "var/evidence/index/summary.json")
    catalog_path = os.getenv("LABEL_CATALOG_PATH", "configs/labels/label_catalog.v2.json")

    try:
        index = json.load(open(path, "r", encoding="utf-8"))
        cat = json.load(open(catalog_path, "r", encoding="utf-8"))
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="index not ready")

    # 간단 합성: period/bucket 필터링은 기존 인덱서 출력 형식에 맞춰 subset
    # 여기서는 mock: groups/labels 빈도 합산
    groups = {g: 0 for g in cat.get("groups", {}).keys()}
    labels = [l["name"] for l in cat.get("labels", [])]
    matrix = {g: {l: 0 for l in labels} for g in groups}

    # index 예: {"rows":[{"label":"reason:infra-latency","count":3,"group":"infra"}, ...]}
    for r in index.get("rows", []):
        g = r.get("group")
        l = r.get("label")
        c = int(r.get("count", 0))
        if g in matrix and l in matrix[g]:
            matrix[g][l] += c

    etag = hashlib.sha256(json.dumps({
        "k": "label-heatmap",
        "period": period,
        "bucket": bucket,
        "catalog_hash": hashlib.sha256(json.dumps(cat, sort_keys=True).encode()).hexdigest(),
        "index_rev": index.get("rev", "0")
    }, sort_keys=True).encode()).hexdigest()

    if if_none_match and if_none_match == etag:
        from fastapi.responses import Response as FastAPIResponse
        return FastAPIResponse(status_code=304)

    return {
        "period": period,
        "bucket": bucket,
        "groups": list(groups.keys()),
        "labels": labels,
        "matrix": matrix,
        "etag": etag
    }
