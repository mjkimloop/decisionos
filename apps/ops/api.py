from __future__ import annotations
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse

from apps.common.metrics import REG
from apps.common.rl import attach_rate_limit
from apps.metrics.registry import METRICS as METRICS_V2
from apps.ops.etag_store_redis import ETagValue, build_store, etag_v2_key
from apps.ops import freeze as freeze_guard
from apps.ops import metrics_burn
from apps.ops.middleware.security import OpsSecurityMiddleware
from apps.policy.pep import require
from apps.policy.rbac_enforce import RbacMapMiddleware
from apps.security.pii import redact_text
from apps.security.pii_middleware import PIIMiddleware


class Ctx:
    def __init__(self) -> None:
        self.tenant = os.getenv("DECISIONOS_TENANT", "t1")
        self.cache_ttl = int(os.getenv("DECISIONOS_OPS_CACHE_TTL", "300"))
        self.etags = build_store()


ctx = Ctx()
app = FastAPI(title="DecisionOS Ops API", version="v0.5.11t")
app.add_middleware(OpsSecurityMiddleware)
attach_rate_limit(app)
rbac_map_path = os.getenv("DECISIONOS_RBAC_MAP", str(Path("apps/policy/rbac_map.yaml")))
default_deny = os.getenv("DECISIONOS_RBAC_DEFAULT_DENY", "0") == "1"
app.add_middleware(RbacMapMiddleware, map_path=rbac_map_path, default_deny=default_deny)
response_fields_env = os.getenv("DECISIONOS_PII_RESPONSE_FIELDS", "")
response_fields = [field.strip() for field in response_fields_env.split(",") if field.strip()]
app.add_middleware(PIIMiddleware, response_fields=response_fields)


def _canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _make_etag(payload: Any) -> str:
    return f'W/"{hashlib.sha256(_canonical(payload).encode()).hexdigest()}"'


def _etag_key(route: str, params: Dict[str, Any]) -> str:
    base = _canonical({"route": route, "params": params})
    return hashlib.sha256(base.encode()).hexdigest()


def _now() -> float:
    return time.time()


async def _require_ops_read() -> bool:
    require("ops:read")
    return True


def _maybe_304(request: Request, route: str, params: Dict[str, Any], builder):
    cache_key = _etag_key(route, params)
    store_key = etag_v2_key(ctx.tenant, route, cache_key)
    cached = ctx.etags.get(store_key)
    inm = request.headers.get("if-none-match")
    ims = request.headers.get("if-modified-since")

    if cached:
        if inm and inm == cached.etag:
            return Response(status_code=304)
        if ims:
            try:
                if float(ims) >= cached.last_modified:
                    return Response(status_code=304)
            except Exception:
                pass

    payload = builder()
    etag = _make_etag(payload)
    lm = _now()
    ctx.etags.set(store_key, ETagValue(etag=etag, last_modified=lm), ttl=ctx.cache_ttl)

    resp = JSONResponse(payload, status_code=200)
    resp.headers["ETag"] = etag
    resp.headers["Last-Modified"] = str(lm)
    resp.headers["Cache-Control"] = f"public, max-age={ctx.cache_ttl}"
    resp.headers["X-Delta-Base-ETag"] = etag
    return resp


@app.get("/ops/cards/reason-trends")
async def reason_trends(
    request: Request,
    q: Optional[str] = None,
    _: bool = Depends(_require_ops_read),
):
    def build():
        sample = q or "연락 test@example.com / 010-1234-5678"
        return {
            "data": {
                "window": {"start": int(_now()) - 3600, "end": int(_now())},
                "groups": [
                    {"group": "infra", "score": 1.4, "labels": [{"k": "reason:infra-latency", "count": 3}]},
                    {"group": "perf", "score": 1.2, "labels": [{"k": "reason:perf", "count": 2}]},
                ],
                "sample": {"redacted": redact_text(sample)},
            }
        }

    params = {"q": q or ""}
    return _maybe_304(request, "/ops/cards/reason-trends", params, build)


@app.get("/ops/cards/top-impact")
async def top_impact(
    request: Request,
    n: int = 5,
    _: bool = Depends(_require_ops_read),
):
    def build():
        items = [
            {"label": "reason:infra-latency", "impact": 0.82},
            {"label": "reason:perf", "impact": 0.61},
            {"label": "reason:canary", "impact": 0.40},
        ][: max(1, min(n, 10))]
        return {"data": {"top": items, "n": n}}

    params = {"n": n}
    return _maybe_304(request, "/ops/cards/top-impact", params, build)


@app.get("/ops/change/window")
async def change_window(
    service: str = os.getenv("DECISIONOS_SERVICE", "core"),
    labels: str = "",
    _: bool = Depends(_require_ops_read),
):
    win_payload = []
    for w in freeze_guard.load_windows():
        win_payload.append(
            {
                "name": w.name,
                "services": list(w.services),
                "allow_tags": list(w.allow_tags),
                "start": w.start.isoformat() if w.start else None,
                "end": w.end.isoformat() if w.end else None,
            }
        )
    blocked, reason = freeze_guard.is_freeze_active(service=service, labels=[lbl.strip() for lbl in labels.split(",") if lbl.strip()])
    return {"data": {"blocked": blocked, "reason": reason, "service": service, "windows": win_payload}}


@app.get("/ops/change/breakglass")
async def change_breakglass(_: bool = Depends(_require_ops_read)):
    manifest_path = os.getenv("DECISIONOS_BREAK_GLASS_MANIFEST", "var/change/breakglass.json")
    data = {"active": freeze_guard.has_valid_break_glass(), "manifest": {}}
    path = Path(manifest_path)
    if path.exists():
        try:
            data["manifest"] = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data["manifest"] = {"error": "invalid"}
    return {"data": data}


@app.get("/ops/cards/burn-trends")
async def burn_trends(
    request: Request,
    window: str = "5m",
    _: bool = Depends(_require_ops_read),
):
    def build():
        report_path = os.getenv("BURN_REPORT_PATH", "var/ci/burn_report.json")
        policy_path = os.getenv("BURN_POLICY_PATH", "configs/slo/burn_policy.yaml")
        report = metrics_burn.ensure_report(report_path, policy_path)
        card = metrics_burn.card_payload(report, None if window == "all" else window)
        return {"data": card}

    params = {"window": window}
    return _maybe_304(request, "/ops/cards/burn-trends", params, build)


@app.get("/healthz")
async def healthz():
    return PlainTextResponse("ok", status_code=200)


@app.get("/readyz")
async def readyz():
    try:
        test_key = etag_v2_key(ctx.tenant, "/readyz", "probe")
        ctx.etags.set(test_key, ETagValue(etag="W/probe", last_modified=_now()), ttl=5)
        _ = ctx.etags.get(test_key)
        return JSONResponse({"status": "ready"}, status_code=200)
    except Exception as exc:
        return JSONResponse({"status": "degraded", "error": str(exc)}, status_code=503)


@app.get("/metrics")
async def metrics():
    """Prometheus-compatible text metrics endpoint."""
    # Combine both metrics registries
    text_v1 = REG.render_text()
    text_v2 = METRICS_V2.export_prom_text()
    combined = text_v1 + "\n" + text_v2
    return PlainTextResponse(combined, media_type="text/plain; version=0.0.4")


if __name__ == "__main__":
    port = int(os.getenv("OPS_PORT", "8081"))
    try:
        import uvicorn  # type: ignore

        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception:
        from fastapi.testclient import TestClient

        client = TestClient(app)
        print(client.get("/healthz").text)
