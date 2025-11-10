from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from apps.common.timeutil import time_utcnow, within_clock_skew
from apps.judge.metrics import JudgeMetrics
from apps.judge.crypto import MultiKeyLoader, verify_with_multikey
from apps.judge.replay_plugins import RedisReplayStore, ReplayStoreABC, SQLiteReplayStore
from apps.judge import slo_judge
from apps.policy.pep import require

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

        ok_sig, reason = verify_with_multikey(payload, signature, key_id, _key_loader)
        if not ok_sig:
            status_code = 401
            request.state.sig_error = True
            raise HTTPException(status_code=401, detail=f"signature mismatch ({reason})")

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

    @app.get("/readyz")
    async def readyz(request: Request):
        if getattr(request.app.state, "replay_store", None) is None:
            raise HTTPException(status_code=503, detail="replay store unavailable")
        return {"status": "ready"}

    @app.get("/metrics")
    async def metrics_endpoint(request: Request):
        summary = request.app.state.metrics.summary()
        return summary

    return app


app = create_app()


__all__ = ["app", "create_app"]
