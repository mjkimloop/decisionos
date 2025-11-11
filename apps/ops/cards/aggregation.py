from __future__ import annotations
import json, os, hashlib, base64
from collections import Counter, defaultdict
from typing import Dict, Any, List, Tuple, Optional

CAT_PATH = os.environ.get("LABEL_CATALOG_PATH", "configs/ops/label_catalog.json")
GROUP_PATH = os.environ.get("REASON_GROUPS_PATH", "configs/ops/reason_groups.json")

def _load(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def label_catalog_hash() -> str:
    cat = _load(CAT_PATH)
    return hashlib.sha256(json.dumps(cat, sort_keys=True).encode()).hexdigest()

def palette_with_desc() -> Dict[str, Dict[str,str]]:
    cat = _load(CAT_PATH)
    out = {}
    for x in cat.get("labels", []):
        if x["name"].startswith("reason:"):
            out[x["name"]] = {"color": x.get("color"), "description": x.get("description","")}
    return out

def _group_weights() -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    groups = _load(GROUP_PATH)
    weights = {k: float(v) for k, v in groups.get("weights", {}).items()}
    return groups.get("groups", []), weights

def aggregate_reasons(reasons: List[str], top: int = 5) -> Dict[str, Any]:
    groups_cfg, weights = _group_weights()
    hits = Counter(reasons)
    # 그룹 카운트
    grp_counts = defaultdict(int)
    for g in groups_cfg:
        gname = g["name"]
        match = set(g["match"])
        cnt = sum(hits[r] for r in hits if r in match or any(r.startswith(m.rstrip("*")) for m in match))
        grp_counts[gname] += cnt
    # 가중치 점수
    weighted = {g: grp_counts[g] * float(weights.get(g, 1.0)) for g in grp_counts}
    # Top N
    top_groups = [{"name": k, "score": v} for k, v in sorted(weighted.items(), key=lambda x: x[1], reverse=True)[:top]]
    top_labels = [{"name": k, "count": v} for k, v in hits.most_common(top)]
    return {
        "raw": dict(hits),
        "groups": dict(grp_counts),
        "weighted": weighted,
        "top_groups": top_groups,
        "top_labels": top_labels,
        "weights": weights,
    }

def etag_seed() -> str:
    # 유지: 카탈로그 SHA를 ETag seed로 사용
    return label_catalog_hash()

# Backward compat - keep old function name
def rollup_counts(reasons: List[str]) -> Dict[str, Any]:
    """Legacy function - use aggregate_reasons instead"""
    agg = aggregate_reasons(reasons, top=5)
    return {
        "raw": agg["raw"],
        "groups": agg["groups"],
        "weighted": agg["weighted"],
        "top": [(k, v) for k, v in agg["weighted"].items()]
    }

# ---- Delta Token/ETag ----
def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def _b64u_dec(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

def make_snapshot_payload(window: Dict[str,str], raw_counts: Dict[str,int], catalog_sha: str) -> Dict[str,Any]:
    return {"v":"1","catalog_sha": catalog_sha, "window": window, "raw": raw_counts}

def snapshot_etag(payload: Dict[str,Any]) -> str:
    h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return f'W/"sha256:{h}"'

def snapshot_token(payload: Dict[str,Any]) -> str:
    blob = json.dumps(payload, sort_keys=True).encode()
    return "v1." + _b64u(blob)

def try_decode_token(token: str) -> Optional[Dict[str,Any]]:
    try:
        if not token.startswith("v1."): return None
        data = _b64u_dec(token.split("v1.",1)[1])
        obj = json.loads(data.decode())
        return obj if obj.get("v") == "1" else None
    except Exception:
        return None

def diff_counts(prev: Dict[str,int], curr: Dict[str,int]) -> Dict[str,Any]:
    added, removed, changed = {}, {}, {}
    keys = set(prev) | set(curr)
    for k in keys:
        a, b = prev.get(k,0), curr.get(k,0)
        if a == 0 and b > 0: added[k] = b
        elif b == 0 and a > 0: removed[k] = a
        elif a != b: changed[k] = {"from": a, "to": b, "delta": b-a}
    return {"added": added, "removed": removed, "changed": changed}
