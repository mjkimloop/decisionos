from __future__ import annotations
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from typing import Any, Dict, Optional
import os, json, hashlib, time
from datetime import datetime, timezone
from apps.policy.pep import require

API = FastAPI(title="DecisionOS Ops API")

EVIDENCE_INDEX = os.getenv("DECISIONOS_EVIDENCE_INDEX", "var/evidence/index.json")

def _utc(dt: float) -> str:
    return datetime.fromtimestamp(dt, tz=timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

def _load_index() -> Dict[str, Any]:
    if not os.path.exists(EVIDENCE_INDEX):
        return {"files": [], "last_updated": 0, "sha": ""}
    with open(EVIDENCE_INDEX, "rb") as f:
        data = f.read()
    try:
        j = json.loads(data.decode("utf-8"))
    except Exception:
        j = {"files": []}
    stat = os.stat(EVIDENCE_INDEX)
    j.setdefault("last_updated", int(stat.st_mtime))
    j.setdefault("sha", hashlib.sha256(data).hexdigest())
    return j

def _compute_etag(index: Dict[str, Any]) -> str:
    key = f"{index.get('sha','')}:{index.get('last_updated',0)}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]

async def rbac_guard(_: Request):
    require("ops:read")

@API.get("/ops/cards/reason-trends", dependencies=[Depends(rbac_guard)])
def get_reason_trends(req: Request):
    idx = _load_index()
    etag = _compute_etag(idx)
    last_mod = _utc(idx.get("last_updated", int(time.time())))
    inm = req.headers.get("if-none-match")
    ims = req.headers.get("if-modified-since")

    if inm == etag or (ims and ims == last_mod):
        return Response(status_code=304)

    src = os.getenv("DECISIONOS_REASON_TRENDS", "var/ops/cards/reason_trends.json")
    if os.path.exists(src):
        with open(src, "r", encoding="utf-8") as f:
            payload = json.load(f)
    else:
        payload = {"series": [], "updated_at": datetime.now(timezone.utc).isoformat()}

    resp = JSONResponse(payload)
    resp.headers["ETag"] = etag
    resp.headers["Last-Modified"] = last_mod
    resp.headers["Cache-Control"] = "no-cache, must-revalidate"
    resp.headers["Surrogate-Control"] = "max-age=30"
    return resp

@API.get("/ops/cards/top-impact", dependencies=[Depends(rbac_guard)])
def get_top_impact(req: Request):
    idx = _load_index()
    etag = _compute_etag(idx)
    last_mod = _utc(idx.get("last_updated", int(time.time())))
    inm = req.headers.get("if-none-match")
    ims = req.headers.get("if-modified-since")
    if inm == etag or (ims and ims == last_mod):
        return Response(status_code=304)

    src = os.getenv("DECISIONOS_TOP_IMPACT", "var/ops/cards/top_impact.json")
    if os.path.exists(src):
        with open(src, "r", encoding="utf-8") as f:
            payload = json.load(f)
    else:
        payload = {"items": [], "updated_at": datetime.now(timezone.utc).isoformat()}

    resp = JSONResponse(payload)
    resp.headers["ETag"] = etag
    resp.headers["Last-Modified"] = last_mod
    resp.headers["Cache-Control"] = "no-cache, must-revalidate"
    resp.headers["Surrogate-Control"] = "max-age=30"
    return resp

@API.get("/healthz")
def healthz():
    return PlainTextResponse("ok")

def main():
    import uvicorn
    uvicorn.run(API, host="0.0.0.0", port=int(os.getenv("PORT", "8081")))

if __name__ == "__main__":
    main()
