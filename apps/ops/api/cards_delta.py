from __future__ import annotations

import email.utils
import hashlib
import json
import os
import random
import time
from typing import Any, Dict

from fastapi import APIRouter, Request, Response

from apps.ops.cache.etag_calc import compute_strong_etag
from apps.ops.api.cards_data import compute_reason_trends
from apps.ops.cache.snapshot_store import SnapshotStore
from apps.policy.rbac_enforce import require_scopes
from apps.common.compress import should_compress, gzip_bytes, negotiate_gzip

# Optional metrics
try:
    from apps.metrics.registry import METRICS_V2 as METRICS
except Exception:
    METRICS = None

TENANT = os.getenv("DECISIONOS_TENANT", "").strip()
CATALOG_SHA = os.getenv("DECISIONOS_LABEL_CATALOG_SHA", "").strip()
_TTL = int(os.getenv("DECISIONOS_CARDS_TTL", "60"))
_SNAP = SnapshotStore()
_FORCE_FULL_PROBE_PCT = int(os.getenv("DECISIONOS_DELTA_FORCE_FULL_PROBE_PCT", "0") or "0")

router = APIRouter(
    prefix="/ops/cards",
    tags=["ops-cards"],
    dependencies=[require_scopes("ops:read")],
)


def _cache_key(q: Dict[str, Any]) -> str:
    """Prevent key collision by folding tenant/catalog/q into the key."""
    qhash = hashlib.sha1(json.dumps(q, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    parts = [p for p in (TENANT, "cards:reason-trends", CATALOG_SHA, qhash) if p]
    return ":".join(parts)


def _small_body_fingerprint(obj: dict, topn: int = 10) -> str:
    """Lightweight fingerprint to catch sparse content changes."""
    top = obj.get("top_reasons", [])[:topn]
    core = json.dumps(top, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(core).hexdigest()


def _compute_etag_seed(index_path: str, tenant: str, catalog_sha: str, query_hash: str) -> str:
    """외부 테스트(property)용: 인덱스 파일 내용을 읽어 ETag 시드를 생성."""
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    buckets = data.get("buckets") or []
    reason_scores: Dict[str, float] = {}
    for b in buckets:
        reasons = b.get("reasons") or {}
        for lbl, cnt in reasons.items():
            reason_scores[lbl] = reason_scores.get(lbl, 0.0) + float(cnt or 0)
    top = sorted(reason_scores.items(), key=lambda kv: kv[1], reverse=True)[:10]
    fp = hashlib.sha256(json.dumps(top, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    mtime = 0.0
    try:
        mtime = os.path.getmtime(index_path)
    except Exception:
        pass
    seed = {"tenant": tenant, "catalog": catalog_sha, "q": query_hash, "mtime": mtime, "fp": fp}
    return json.dumps(seed, sort_keys=True, separators=(",", ":"))


def _etag(seed: str) -> str:
    return '"' + hashlib.sha256(seed.encode()).hexdigest() + '"'


def _httpdate(ts: float) -> str:
    return email.utils.formatdate(ts, usegmt=True)


_COUNTERS = {"cards_200": 0, "cards_304": 0, "cards_delta": 0}


@router.get("/reason-trends")
async def reason_trends(request: Request, period: str = "7d", bucket: str = "day"):
    q = {"period": period, "bucket": bucket}
    body_obj = compute_reason_trends(period=period, bucket=bucket)
    body_json = json.dumps(body_obj, ensure_ascii=False)
    index_path = (body_obj.get("_meta") or {}).get("index_path") or os.getenv("DECISIONOS_EVIDENCE_INDEX", "")
    query_hash = hashlib.sha1(json.dumps(q, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:8]
    salt = f"t={TENANT};c={CATALOG_SHA};q={query_hash}"
    etag = compute_strong_etag(index_path, salt=salt)

    if request.headers.get("If-None-Match") == etag:
        headers = {
            "ETag": etag,
            "Cache-Control": f"private, max-age={_TTL}",
            "Vary": "Authorization, X-Scopes, X-Tenant, Accept-Encoding, If-None-Match, If-Modified-Since",
            "Content-Length": "0",
        }
        resp = Response(content=b"", status_code=304, headers=headers)
        _COUNTERS["cards_304"] += 1
        if METRICS:
            await METRICS.inc("decisionos_cards_etag_total", {"result": "hit"})
        return resp

    snap_key = _cache_key(q)
    prev = _SNAP.get(snap_key)
    delta = None
    if prev:
        try:
            prev_obj = json.loads(prev[0])
            prev_top = {x["reason"]: x["score"] for x in prev_obj.get("top_reasons", [])}
            curr_top = {x["reason"]: x["score"] for x in body_obj.get("top_reasons", [])}
            added = {k: curr_top[k] for k in curr_top.keys() - prev_top.keys()}
            removed = {k: prev_top[k] for k in prev_top.keys() - curr_top.keys()}
            changed = {
                k: curr_top[k] - prev_top.get(k, 0)
                for k in curr_top.keys() & prev_top.keys()
                if abs(curr_top[k] - prev_top[k]) > 1e-6
            }
            delta = {"added": added, "removed": removed, "changed": changed}
        except Exception:
            delta = None

    base = request.headers.get("X-Delta-Base-ETag")
    forced_full = 0 < _FORCE_FULL_PROBE_PCT and random.randint(0, 99) < _FORCE_FULL_PROBE_PCT
    delta_accepted = "1" if delta is not None else "0"
    if forced_full:
        delta = None
        delta_accepted = "0"
    elif base and base != etag:
        delta = None
        delta_accepted = "0"

    payload = {"data": body_obj, "delta": delta, "_meta": {"tenant": TENANT, "catalog_sha": CATALOG_SHA}}
    payload_json = json.dumps(payload, ensure_ascii=False)
    payload_bytes = payload_json.encode("utf-8")

    # Compression negotiation (v0.5.11u-7)
    accept_encoding = request.headers.get("Accept-Encoding", "")
    use_gzip = negotiate_gzip(accept_encoding) and should_compress(len(payload_bytes))

    if use_gzip:
        content = gzip_bytes(payload_bytes)
        content_encoding = "gzip"
        encoding_label = "gzip"
    else:
        content = payload_bytes
        content_encoding = None
        encoding_label = "identity"

    resp = Response(content=content, media_type="application/json")
    resp.headers["ETag"] = etag  # ETag is representation-invariant (same for gzip/identity)
    resp.headers["Last-Modified"] = _httpdate(time.time())
    resp.headers["Cache-Control"] = f"private, max-age={_TTL}"
    resp.headers["Vary"] = "Authorization, X-Scopes, X-Tenant, Accept-Encoding, If-None-Match, If-Modified-Since"
    resp.headers["X-Delta-Accepted"] = delta_accepted
    resp.headers["X-Delta-Base-ETag"] = etag
    if forced_full:
        resp.headers["X-Delta-Probe"] = "1"
    if content_encoding:
        resp.headers["Content-Encoding"] = content_encoding

    _SNAP.set(snap_key, body_json)
    _COUNTERS["cards_200"] += 1
    if delta:
        _COUNTERS["cards_delta"] += 1
    if METRICS:
        await METRICS.inc("decisionos_cards_etag_total", {"result": "miss"})
        await METRICS.inc("decisionos_cards_encoded_total", {"encoding": encoding_label})
    return resp
