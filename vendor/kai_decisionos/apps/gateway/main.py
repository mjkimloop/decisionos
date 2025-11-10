from __future__ import annotations

import os
from typing import Optional, List

from fastapi import FastAPI, Depends, Header, HTTPException, status

from packages.common.config import settings
from apps.obs import install_from_env as install_obs_middleware
from .routers import (
    decide,
    simulate,
    explain,
    cases,
    tasks,
    appeals,
    queues,
    sla,
    orgs,
    projects,
    entitlements,
    usage,
    billing,
    cost_guard,
    consent,
    metrics,
    packs,
    analytics,
    feedback,
    backlog,
    onboarding,
    public_info,
    billing_selfserve,
    payments,
    tax as tax_router,
    receipt as receipt_router,
    pay as pay_router,
    kyc,
    auth_oidc,
    rbac as rbac_router,
    invites,
    personal_tokens,
    admin_ui,
    connectors,
    contracts as contracts_router,
    pipelines as pipelines_router,
    quality,
    catalog,
    search as search_router,
    ext_deploy,
    marketplace as marketplace_router,
    policies as policies_router,
    webhooks as webhooks_router,
    boundaries as boundaries_router,
    reconcile as reconcile_router,
)
from .routers import region as region_router
from .routers import health as health_router
from .routers import failover as failover_router
from .routers import usage_events as usage_events_router
from .routers import usage_summary as usage_summary_router
from .routers import billing_webhook as billing_webhook_router
from .routers import lineage as lineage_router
from .routers import products as products_router
app = FastAPI(title="DecisionOS Gateway", version="0.1")


def api_key_guard(
    x_api_key: Optional[str] = Header(default=None, alias="X-Api-Key"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
):
    expected = os.getenv("API_KEY", settings.admin_api_key or "dev-key")
    bearer = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", 1)[1]
    if x_api_key == expected or bearer == expected:
        return True
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


def RBAC(required: List[str]):
    def _dep(x_role: Optional[str] = Header(default=None, alias="X-Role")):
        if not required:
            return True
        role = (x_role or os.getenv("DEFAULT_ROLE", "admin")).lower()
        if role in {r.lower() for r in required}:
            return True
        raise HTTPException(status_code=403, detail="forbidden")

    return _dep


@app.get("/health")
def health():
    return {"ok": True}


# Core routers
app.include_router(decide.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "agent"]))])
app.include_router(simulate.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin"]))])
app.include_router(explain.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "auditor"]))])

# HITL & Tenancy/Billing/Usage routers
app.include_router(cases.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "agent"]))])
app.include_router(tasks.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "agent"]))])
app.include_router(appeals.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "agent", "auditor"]))])
app.include_router(queues.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin"]))])
app.include_router(sla.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "auditor"]))])
app.include_router(orgs.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin"]))])
app.include_router(projects.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin"]))])
app.include_router(entitlements.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "agent"]))])
app.include_router(usage.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "auditor"]))])
app.include_router(billing.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin"]))])
app.include_router(cost_guard.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "auditor"]))])
app.include_router(packs.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "agent", "auditor"]))])
app.include_router(analytics.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "analyst", "agent"]))])
app.include_router(feedback.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "analyst", "agent"]))])
app.include_router(backlog.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin"]))])
app.include_router(onboarding.router)
app.include_router(public_info.router)
app.include_router(billing_selfserve.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin"]))])
app.include_router(payments.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "finance"]))])
app.include_router(pay_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "finance"]))])
app.include_router(tax_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "finance"]))])
app.include_router(receipt_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "finance"]))])
app.include_router(reconcile_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "finance"]))])
app.include_router(kyc.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "finance", "auditor"]))])
app.include_router(auth_oidc.router)
app.include_router(rbac_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin"]))])
app.include_router(invites.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin"]))])
app.include_router(personal_tokens.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "developer"]))])
app.include_router(admin_ui.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin"]))])
app.include_router(connectors.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "developer"]))])
app.include_router(contracts_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "developer"]))])
app.include_router(pipelines_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "developer"]))])
app.include_router(quality.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "analyst"]))])
app.include_router(catalog.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "analyst"]))])
app.include_router(search_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "analyst", "agent"]))])
app.include_router(lineage_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "analyst"]))])
app.include_router(products_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin"]))])
app.include_router(ext_deploy.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "developer"]))])
app.include_router(webhooks_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "developer"]))])
app.include_router(marketplace_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "developer"]))])
app.include_router(policies_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin"]))])
app.include_router(boundaries_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "auditor"]))])
app.include_router(webhooks_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "developer"]))])

app.include_router(marketplace_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "developer"]))])
# Consent & Metrics routers
app.include_router(consent.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin", "agent", "auditor"]))])
app.include_router(metrics.router, dependencies=[Depends(api_key_guard)])

# 개발 모드: DB URL이 설정된 경우 테이블 생성
from packages.common.config import settings as _settings

try:
    if _settings.db_url:
        from apps.db.init import init_db as _init_db

        @app.on_event("startup")
        def _startup_db():
            try:
                _init_db()
            except Exception:
                # DB 미설정/접속 실패는 앱 기동을 막지 않음(개발 모드)
                pass
except Exception:
    pass

# Metrics middleware install
from .middleware import metrics as _metrics_mw

try:
    _metrics_mw.install(app)
except Exception:
    pass

# Tenant header enforcement
from .middleware import tenant as _tenant_mw
try:
    _tenant_mw.install(app)
except Exception:
    pass

# Observability (OTel) middleware
try:
    install_obs_middleware(app)
except Exception:
    pass


# Gate-E routers
app.include_router(usage_events_router.router, dependencies=[Depends(api_key_guard)])
app.include_router(usage_summary_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin","auditor"]))])
app.include_router(billing_webhook_router.router, dependencies=[Depends(api_key_guard)])

# Gate-F region router
app.include_router(region_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin","auditor"]))])

# Gate-G health/failover routers
app.include_router(health_router.router, dependencies=[Depends(api_key_guard)])
app.include_router(failover_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin"]))])

# Correlation middleware
from .middleware import correlation as _corr_mw
try:
    _corr_mw.install(app)
except Exception:
    pass

# Gate-H admin metrics router
from .routers import admin as admin_router
app.include_router(admin_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin","auditor"]))])

# Gate-I policy/vault/HITL UI routers
from .routers import policy as policy_router
from .routers import vault as vault_router
from .routers import hitl_ui as hitl_ui_router
app.include_router(policy_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin"]))])
app.include_router(vault_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin"]))])
app.include_router(hitl_ui_router.router, dependencies=[Depends(api_key_guard), Depends(RBAC(["admin","agent"]))])
