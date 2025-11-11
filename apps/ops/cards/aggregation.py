from __future__ import annotations
import json, os, hashlib
from collections import Counter, defaultdict
from typing import Dict, Any, List

CAT_PATH = os.environ.get("LABEL_CATALOG_PATH", "configs/ops/label_catalog.json")
GROUP_PATH = os.environ.get("REASON_GROUPS_PATH", "configs/ops/reason_groups.json")

def _load(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def palette_with_desc() -> Dict[str, Dict[str,str]]:
    cat = _load(CAT_PATH)
    out = {}
    for x in cat.get("labels", []):
        if x["name"].startswith("reason:"):
            out[x["name"]] = {"color": x.get("color"), "description": x.get("description","")}
    return out

def rollup_counts(reasons: List[str]) -> Dict[str, Any]:
    groups = _load(GROUP_PATH)
    weights = groups.get("weights", {})
    hits = Counter(reasons)
    grp_map = defaultdict(int)
    for g in groups.get("groups", []):
        gname = g["name"]
        ms = set(g["match"])
        count = sum(hits[r] for r in hits if r in ms or any(r.startswith(m.rstrip("*")) for m in ms))
        grp_map[gname] += count
    score = {g: grp_map[g] * float(weights.get(g, 1.0)) for g in grp_map}
    top = sorted(score.items(), key=lambda x: x[1], reverse=True)
    return {"raw": hits, "groups": dict(grp_map), "weighted": score, "top": top}

def etag_seed() -> str:
    cat = _load(CAT_PATH)
    return hashlib.sha256(json.dumps(cat, sort_keys=True).encode()).hexdigest()
