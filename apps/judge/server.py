from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from apps.common.metrics import REG
from apps.common.rl import attach_rate_limit
from apps.common.timeutil import time_utcnow, within_clock_skew
from apps.judge.crypto import MultiKeyLoader, SignatureInvalid, verify_signature_safe
from apps.judge import slo_judge
from apps.judge.metrics import JudgeMetrics
from apps.judge.metrics_readyz import READYZ_METRICS
from apps.judge.middleware.security import JudgeSecurityMiddleware
from apps.judge.readyz import build_readyz_router, default_readyz_checks
from apps.judge.replay_plugins import RedisReplayStore, ReplayStoreABC, SQLiteReplayStore
from apps.policy.pep import require
from apps.policy.rbac_enforce import RbacMapMiddleware
from apps.security.pii_middleware import PIIMiddleware

_DEFAULT_WINDOW = int(os.getenv("DECISIONOS_JUDGE_METRIC_WINDOW", "600"))
_metrics = JudgeMetrics(window_seconds=_DEFAULT_WINDOW)
_key_loader = MultiKeyLoader()

def _build_replay_store() -> ReplayStoreABC:
    backend = os.getenv("DECISIONOS_REPLAY_BACKEND", "sqlite").lower()
    if backend == "redis":
        url = os.getenv("DECISIONOS_REDIS_URL", "redis://localhost:6379/0")
        return RedisReplayStore(url=url)
    path = os.getenv("DECISIONOS_REPLAY_SQLITE", "var/judge/replay.sqlite")
    return SQLiteReplayStore(path=path)


def create_app(replay_store: Optional[ReplayStoreABC] = None) -> FastAPI:
    app = FastAPI(title="DecisionOS Judge", version="0.5.11j")
    app.state.metrics = _metrics
    app.state.replay_store = replay_store or _build_replay_store()
    response_fields_env = os.getenv("DECISIONOS_PII_RESPONSE_FIELDS", "")
    response_fields = [field.strip() for field in response_fields_env.split(",") if field.strip()]
    app.add_middleware(JudgeSecurityMiddleware)
    attach_rate_limit(app)
    app.add_middleware(PIIMiddleware, response_fields=response_fields)
    rbac_map_path = os.getenv("DECISIONOS_RBAC_MAP", str(Path("apps/policy/rbac_map.yaml")))
    default_deny = os.getenv("DECISIONOS_RBAC_DEFAULT_DENY", "0") == "1"
    app.add_middleware(RbacMapMiddleware, map_path=rbac_map_path, default_deny=default_deny)
    fail_closed = os.getenv("DECISIONOS_READY_FAIL_CLOSED", "1") == "1"
    ready_checks = default_readyz_checks(_key_loader, app.state.replay_store)
    from apps.judge.readyz import build_readyz_router

    app.include_router(build_readyz_router(ready_checks, fail_closed=fail_closed))

    @app.post("/judge")
    async def post_judge(request: Request) -> JSONResponse:
        request.state.sig_error = False
        metrics: JudgeMetrics = request.app.state.metrics
        status_code = 200

        try:
            payload = await request.json()
        except Exception as exc:  # pragma: no cover - fastapi already handles
            status_code = 400
            raise HTTPException(status_code=400, detail="invalid json") from exc

        headers = request.headers
        key_id = headers.get("X-Key-Id", "k1")
        signature = headers.get("X-DecisionOS-Signature")
        nonce = headers.get("X-DecisionOS-Nonce")
        ts_raw = headers.get("X-DecisionOS-Timestamp")

        if not signature or nonce is None or ts_raw is None:
            status_code = 400
            raise HTTPException(status_code=400, detail="missing signature headers")

        try:
            ts_epoch = int(float(ts_raw))
        except ValueError:
            status_code = 400
            raise HTTPException(status_code=400, detail="invalid timestamp header")
        ts_dt = datetime.fromtimestamp(ts_epoch, tz=timezone.utc)

        # Security (v0.5.11u-5): use safe verification with generic error message
        try:
            verify_signature_safe(payload, signature, key_id, _key_loader)
        except SignatureInvalid:
            status_code = 401
            request.state.sig_error = True
            # Generic message (detailed reason logged internally)
            raise HTTPException(status_code=401, detail="invalid signature")

        now = time_utcnow()
        if not within_clock_skew(now, ts_dt, 90):
            status_code = 401
            raise HTTPException(status_code=401, detail="timestamp skew exceeded")

        store: ReplayStoreABC = request.app.state.replay_store
        if store.seen_or_insert(key_id, nonce, ts_epoch):
            status_code = 401
            request.state.sig_error = True
            raise HTTPException(status_code=401, detail="replay detected")

        evidence = payload.get("evidence")
        slo = payload.get("slo")
        if not isinstance(evidence, dict) or not isinstance(slo, dict):
            status_code = 400
            raise HTTPException(status_code=400, detail="invalid payload structure")

        try:
            require("judge:run")
        except PermissionError:
            status_code = 403
            raise HTTPException(status_code=403, detail="rbac denied")

        decision, reasons = slo_judge.evaluate(evidence, slo)
        resp = {
            "decision": decision,
            "reasons": reasons,
            "ts": time_utcnow().isoformat().replace("+00:00", "Z"),
        }
        return JSONResponse(resp)

        # metrics recorded in middleware (below)

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start = time.perf_counter()
        if not hasattr(request.state, "sig_error"):
            request.state.sig_error = False
        try:
            response = await call_next(request)
            status_code = response.status_code
        except HTTPException as exc:
            status_code = exc.status_code
            raise
        except Exception:  # pragma: no cover
            status_code = 500
            raise
        finally:
            latency_ms = (time.perf_counter() - start) * 1000
            sig_flag = getattr(request.state, "sig_error", False)
            request.app.state.metrics.observe(latency_ms, status_code, sig_flag)
        return response

    @app.get("/healthz")
    async def healthz() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics")
    async def metrics_endpoint(request: Request):
        # Export readyz sliding window gauges before rendering
        READYZ_METRICS.export_gauges()
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(REG.render_text(), media_type="text/plain")

    return app


app = create_app()


__all__ = ["app", "create_app"]
