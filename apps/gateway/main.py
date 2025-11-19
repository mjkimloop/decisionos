from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI

from apps.gateway.routers import consent, metrics
from apps.gateway.security.cors import attach_strict_cors
from apps.metrics.collectors import add_latency_middleware
from apps.policy.rbac_enforce import RbacMapMiddleware
from apps.ops.api.cards_delta import router as cards_router


app = FastAPI(title="DecisionOS Gateway", version="v0.1.3")

# CORS: strict allowlist enforcement (v0.5.11u-5)
attach_strict_cors(app)

# RBAC 맵: 기본은 configs/security/rbac_map.yaml, 환경변수로 재정의
rbac_map_path = os.getenv("DECISIONOS_RBAC_MAP_PATH", str(Path("configs/security/rbac_map.yaml")))
default_deny = os.getenv("DECISIONOS_RBAC_DEFAULT_DENY", "0") == "1"
app.add_middleware(RbacMapMiddleware, map_path=rbac_map_path, default_deny=default_deny)
# 요청 지표 수집
add_latency_middleware(app)

# 라우터 마운트
app.include_router(consent.router)
app.include_router(metrics.router)
app.include_router(cards_router)


@app.get("/healthz")
async def healthz():
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn  # type: ignore

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("GATEWAY_PORT", "8080")))
