from __future__ import annotations

import csv
import hashlib
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

import httpx
import yaml
import typer
from rich import print

from apps.executor.pipeline import simulate as local_simulate, decide as local_decide
from apps.rule_engine.offline_eval import run_report as run_html_report
from apps.rule_engine.linter import lint_rules
from apps.rule_engine.engine import load_contract
from apps.packs.linter import lint_spec as lint_pack_spec
from apps.packs.validator import load_pack_file, validate_pack_file, validate_spec
from apps.packs.simulator import simulate_pack as run_pack_simulation
from apps.onboarding.models import SignupRequest, BootstrapRequest
from apps.onboarding.service import (
    register_signup as local_register_signup,
    bootstrap_tenant as local_bootstrap_tenant,
    get_status_summary,
    get_support_contacts,
    get_pricing_catalog,
)
from apps.events.sdk import track_event as local_track_event
from apps.analytics.service import (
    summarise_events as local_summarise_events,
    dashboard_html as local_dashboard_html,
)
from apps.feedback.models import FeedbackSubmit
from apps.feedback.store import (
    add_feedback as local_add_feedback,
    list_feedback as local_list_feedback,
)
from apps.feedback.classifier import aggregate_feedback as local_aggregate_feedback
from apps.backlog.models import BacklogSubmit
from apps.backlog.store import (
    add_item as local_add_backlog_item,
    list_items as local_list_backlog_items,
)
from apps.billing.ratebook import list_plans as local_ratebook_plans, get_unit_price as local_get_rate, clear_cache as ratebook_clear_cache
from apps.billing.prorater import prorate_amount as local_prorate_amount
from apps.billing.selfserve import subscribe as local_self_subscribe, get_subscription as local_get_subscription
from apps.billing.reconciler import get_reconciliation as local_get_reconciliation, reconcile_invoice as local_reconcile_invoice
from apps.billing.invoicer import INVOICES
from apps.payments.gateway import record_payment as local_record_payment, list_payments as local_list_payments
from apps.payments import PaymentsService
from apps.payments.core import PaymentsRepository
from apps.payments.adapters import list_adapters as local_payments_adapters
from apps.payments.container import gateway_service, payments_service
from apps.payments.models import Receipt
from apps.receipts.render import render_receipt_assets
from apps.reconcile.matcher import reconciliation_status as local_reconcile_status, reconcile_charge_event as local_reconcile_match
from apps.payments.dunning import (
    mark_overdue as local_mark_overdue,
    get_status as local_dunning_status,
    schedule_followup as local_schedule_followup,
)
from apps.auth.oidc import provider_singleton, generate_state as oidc_generate_state, generate_code as oidc_generate_code
from apps.auth.session import (
    create_session as local_create_session,
    get_session as local_get_session,
    invalidate_session as local_invalidate_session,
)
from apps.auth.jwks import get_jwks as local_get_jwks
from apps.rbac import (
    assign_role as local_assign_role,
    revoke_role as local_revoke_role,
    list_roles as local_list_roles,
    check_permission as local_check_permission,
)
from apps.tenancy.invites import (
    create_invite as local_create_invite,
    list_invites as local_list_invites,
    accept_invite as local_accept_invite,
)
from apps.tenancy.pat import (
    create_token as local_create_pat,
    list_tokens as local_list_pat,
    revoke_token as local_revoke_pat,
)
from apps.catalog.registry import registry as catalog_registry
from apps.catalog.models import CatalogItem
from apps.catalog.indexer import search as catalog_search
from apps.lineage.collector import ingest as lineage_ingest, list_edges as lineage_list_edges
from apps.lineage.graph import graph as lineage_graph, impact as lineage_impact
from apps.lineage.models import LineageEdge
from apps.products.registry import registry as product_registry
from apps.products.schema import ProductSpec, ProductVersion
from apps.products.builder import build_manifest as build_product_manifest
from apps.connectors.sdk import registry as connector_registry
from apps.contracts.schema import load_contract as local_load_contract
from apps.contracts.validator import validate_payload as local_validate_contract_payload
from apps.contracts.compat import compare_versions as local_compare_versions
from apps.pipelines.service import run_pipeline as local_run_pipeline
from apps.quality.metrics import compute_quality as local_compute_quality
from packages.common.config import settings






app = typer.Typer(help="DecisionOS CLI (dosctl)")

audit_app = typer.Typer(help="Audit utilities")

app.add_typer(audit_app, name="audit")
# Seal & helper subcommands
seal_app = typer.Typer(help="Reality-Seal helpers")
app.add_typer(seal_app, name="seal")
consent_app = typer.Typer(help="Consent API helper")
boundary_app = typer.Typer(help="Boundary guard helper")
metrics_app = typer.Typer(help="Metrics API helper")
app.add_typer(consent_app, name="consent")
app.add_typer(boundary_app, name="boundary")
app.add_typer(metrics_app, name="metrics")
packs_app = typer.Typer(help="Pack helpers")
app.add_typer(packs_app, name="packs")
onboarding_app = typer.Typer(help="Onboarding helpers")
app.add_typer(onboarding_app, name="onboarding")
analytics_app = typer.Typer(help="Analytics helpers")
app.add_typer(analytics_app, name="analytics")
feedback_app = typer.Typer(help="Feedback helpers")
app.add_typer(feedback_app, name="feedback")
backlog_app = typer.Typer(help="Backlog helpers")
app.add_typer(backlog_app, name="backlog")
auth_app = typer.Typer(help="Auth helpers")
app.add_typer(auth_app, name="auth")
rbac_app = typer.Typer(help="RBAC helpers")
app.add_typer(rbac_app, name="rbac")
invites_app = typer.Typer(help="Invite helpers")
app.add_typer(invites_app, name="invites")
pat_app = typer.Typer(help="Personal tokens")
app.add_typer(pat_app, name="pat")
pay_app = typer.Typer(help="Payments helpers")
app.add_typer(pay_app, name="pay")
kyc_app = typer.Typer(help="KYC helpers")
app.add_typer(kyc_app, name="kyc")
ext_app = typer.Typer(help="Extension helpers")
app.add_typer(ext_app, name="ext")
webhooks_cli_app = typer.Typer(help="Webhook helpers")
app.add_typer(webhooks_cli_app, name="webhooks")
market_app = typer.Typer(help="Marketplace helpers")
app.add_typer(market_app, name="market")
catalog_app = typer.Typer(help="Catalog helpers")
app.add_typer(catalog_app, name="catalog")
lineage_app = typer.Typer(help="Lineage helpers")
app.add_typer(lineage_app, name="lineage")
products_app = typer.Typer(help="Product helpers")
app.add_typer(products_app, name="product")
connectors_app = typer.Typer(help="Connector registry")
app.add_typer(connectors_app, name="connectors")
contracts_app = typer.Typer(help="Contracts")
app.add_typer(contracts_app, name="contracts")
pipelines_app = typer.Typer(help="Pipelines")
app.add_typer(pipelines_app, name="pipelines")
quality_app = typer.Typer(help="Quality metrics")
app.add_typer(quality_app, name="quality")
_local_payments = PaymentsService(PaymentsRepository({}, {}, {}, {}))\n_local_ext_installs: dict[str, list[dict]] = {}
_local_webhooks: list[dict] = []


@packs_app.command("list")
def packs_list(server: str = typer.Option(None, help="Gateway base URL")):
    if server:
        url = f"{server.rstrip('/')}/api/v1/packs"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url)
            resp.raise_for_status()
            print(resp.json())
        return

    items = []
    for path in _iter_pack_files():
        result = validate_pack_file(path)
        entry = {
            "path": str(path),
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings,
        }
        if result.spec:
            entry["identifier"] = result.spec.identifier()
            entry["domain"] = result.spec.meta.domain
        items.append(entry)
    print(items)


@packs_app.command("lint")
def packs_lint(pack_file: Path):
    spec = load_pack_file(pack_file)
    issues = lint_pack_spec(spec)
    print([issue.model_dump() for issue in issues])


@packs_app.command("validate")
def packs_validate(pack_file: Path, server: str = typer.Option(None, help="Gateway base URL")):
    spec = load_pack_file(pack_file)
    if server:
        url = f"{server.rstrip('/')}/api/v1/packs/validate"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json={"pack": spec.model_dump(mode="json")})
            resp.raise_for_status()
            print(resp.json())
        return
    result = validate_spec(spec)
    print({
        "valid": result.valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "info": result.info,
        "identifier": spec.identifier(),
    })


@packs_app.command("simulate")
def packs_simulate(pack_file: Path, csv_path: Path, label_key: Optional[str] = typer.Option("converted")):
    spec = load_pack_file(pack_file)
    rows = _read_csv_rows(csv_path)
    result = run_pack_simulation(spec, rows, label_key)
    print(result)


@packs_app.command("seed")
def packs_seed(name: str = typer.Option("lending_pack_v1"), output: Path = typer.Option(Path("var/packs"))):
    source = _find_pack_file(name)
    output.mkdir(parents=True, exist_ok=True)
    target = output / f"{name}{source.suffix or '.yaml'}"
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    print({"seeded": str(target)})


@onboarding_app.command("signup")
def onboarding_signup(email: str, company: str, plan: str = typer.Option("trial"), notes: str = typer.Option(""), server: str = typer.Option(None)):
    payload = SignupRequest(email=email, company=company, plan=plan, notes=notes or None)
    if server:
        url = f"{server.rstrip('/')}/api/v1/onboarding/signup"
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, json=payload.model_dump(mode="json"), headers=_default_headers())
            resp.raise_for_status()
            print(resp.json())
        return
    record = local_register_signup(payload)
    print(record.model_dump(mode="json"))


@onboarding_app.command("bootstrap")
def onboarding_bootstrap(signup_id: str, org_name: str, project_name: str, region: str = typer.Option("region-a"), server: str = typer.Option(None)):
    payload = BootstrapRequest(signup_id=signup_id, org_name=org_name, project_name=project_name, region=region)
    if server:
        url = f"{server.rstrip('/')}/api/v1/onboarding/bootstrap"
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, json=payload.model_dump(mode="json"), headers=_default_headers())
            if resp.status_code == 404:
                raise typer.Exit(code=1)
            resp.raise_for_status()
            print(resp.json())
        return
    result = local_bootstrap_tenant(payload)
    print(result.model_dump(mode="json"))


@onboarding_app.command("status")
def onboarding_status(server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/status"
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, headers=_default_headers())
            resp.raise_for_status()
            print(resp.json())
        return
    print(get_status_summary())


@onboarding_app.command("support")
def onboarding_support(server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/support"
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, headers=_default_headers())
            resp.raise_for_status()
            print(resp.json())
        return
    print(get_support_contacts())


@onboarding_app.command("pricing")
def onboarding_pricing(server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/pricing"
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, headers=_default_headers())
            resp.raise_for_status()
            print(resp.json())
        return
    print(get_pricing_catalog())


@analytics_app.command("track")
def analytics_track(
    event: str,
    user_id: Optional[str] = typer.Option(None),
    session_id: Optional[str] = typer.Option(None),
    source: str = typer.Option("cli"),
    metadata: Optional[str] = typer.Option(None, help="JSON metadata"),
    server: str = typer.Option(None),
):
    meta = json.loads(metadata) if metadata else {}
    payload = {
        "event": event,
        "user_id": user_id,
        "session_id": session_id,
        "source": source,
        "metadata": meta,
    }
    if server:
        url = f"{server.rstrip('/')}/api/v1/analytics/events"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    evt = local_track_event(event, user_id=user_id, session_id=session_id, source=source, metadata=meta)
    print({"event": evt.event, "created_at": evt.created_at})


@analytics_app.command("summary")
def analytics_summary(limit: Optional[int] = typer.Option(None), server: str = typer.Option(None)):
    if server:
        params = {"limit": limit} if limit is not None else None
        url = f"{server.rstrip('/')}/api/v1/analytics/summary"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            print(resp.json())
        return
    summary = local_summarise_events(limit=limit)
    print(summary)


@analytics_app.command("dashboard")
def analytics_dashboard(output: Path = typer.Option(Path("var/reports/analytics.html")), limit: Optional[int] = typer.Option(None), server: str = typer.Option(None)):
    if server:
        params = {"limit": limit} if limit is not None else None
        url = f"{server.rstrip('/')}/api/v1/analytics/dashboard"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(resp.text, encoding="utf-8")
            print({"saved": str(output)})
        return
    summary = local_summarise_events(limit=limit)
    html = local_dashboard_html(summary)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    print({"saved": str(output)})


@feedback_app.command("submit")
def feedback_submit(
    rating: int = typer.Argument(..., min=0, max=10),
    comment: str = typer.Option(""),
    user_id: Optional[str] = typer.Option(None),
    channel: str = typer.Option("cli"),
    server: str = typer.Option(None),
):
    payload = FeedbackSubmit(rating=rating, comment=comment or None, user_id=user_id, channel=channel)
    if server:
        url = f"{server.rstrip('/')}/api/v1/feedback/nps"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=payload.model_dump(mode="json"))
            resp.raise_for_status()
            print(resp.json())
        return
    entry = local_add_feedback(payload)
    print(entry.model_dump(mode="json"))


@feedback_app.command("stats")
def feedback_stats(server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/feedback/stats"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url)
            resp.raise_for_status()
            print(resp.json())
        return
    entries = local_list_feedback()
    ratings = [entry.rating for entry in entries]
    print({"n": len(ratings), **local_aggregate_feedback(ratings)})


@backlog_app.command("add")
def backlog_add(
    title: str,
    reach: float,
    impact: float,
    confidence: float,
    effort: float,
    owner: Optional[str] = typer.Option(None),
    tags: str = typer.Option("", help="comma separated tags"),
    server: str = typer.Option(None),
):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    payload = BacklogSubmit(
        title=title,
        reach=reach,
        impact=impact,
        confidence=confidence,
        effort=effort,
        owner=owner,
        tags=tag_list,
    )
    if server:
        url = f"{server.rstrip('/')}/api/v1/backlog/items"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=payload.model_dump(mode="json"))
            resp.raise_for_status()
            print(resp.json())
        return
    item = local_add_backlog_item(payload)
    print(item.model_dump(mode="json"))


@backlog_app.command("list")
def backlog_list(server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/backlog/items"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url)
            resp.raise_for_status()
            print(resp.json())
        return
    items = sorted(local_list_backlog_items(), key=lambda x: x.rice, reverse=True)
    print({"items": [item.model_dump(mode="json") for item in items]})


@auth_app.command("config")
def auth_config(server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/auth/oidc/config"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url)
            resp.raise_for_status()
            print(resp.json())
        return
    state = oidc_generate_state()
    print({
        "issuer": provider_singleton.issuer,
        "authorize_url": provider_singleton.build_authorize_url(state),
        "client_id": provider_singleton.client_id,
        "redirect_uri": provider_singleton.redirect_uri,
        "state": state,
    })


@auth_app.command("login")
def auth_login(code: str = typer.Option(None), state: str = typer.Option(None), server: str = typer.Option(None)):
    code = code or oidc_generate_code()
    state = state or oidc_generate_state()
    payload = {"code": code, "state": state}
    if server:
        url = f"{server.rstrip('/')}/api/v1/auth/oidc/callback"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    tokens = provider_singleton.exchange_code(code, state)
    info = provider_singleton.build_userinfo(tokens["access_token"])
    session = local_create_session(info["sub"])
    print({
        "session_id": session.session_id,
        "userinfo": info,
        "tokens": tokens,
    })


@auth_app.command("session")
def auth_session(session_id: str, server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/auth/oidc/session/{session_id}"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url)
            resp.raise_for_status()
            print(resp.json())
        return
    sess = local_get_session(session_id)
    if not sess:
        print({"error": "session_expired"})
    else:
        print({
            "session_id": sess.session_id,
            "subject": sess.subject,
            "expires_at": sess.expires_at.isoformat(),
        })


@auth_app.command("logout")
def auth_logout(session_id: str, server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/auth/oidc/session/{session_id}"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.delete(url)
            resp.raise_for_status()
            print(resp.json())
        return
    local_invalidate_session(session_id)
    print({"ok": True})


@auth_app.command("jwks")
def auth_jwks(server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/auth/oidc/jwks"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url)
            resp.raise_for_status()
            print(resp.json())
        return
    print(local_get_jwks())


@rbac_app.command("assign")
def rbac_assign(user: str, role: str, server: str = typer.Option(None)):
    payload = {"user": user, "role": role}
    if server:
        url = f"{server.rstrip('/')}/api/v1/rbac/assign"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    local_assign_role(user, role)
    print({"user": user, "roles": sorted(list(local_list_roles(user)))})


@rbac_app.command("revoke")
def rbac_revoke(user: str, role: str, server: str = typer.Option(None)):
    payload = {"user": user, "role": role}
    if server:
        url = f"{server.rstrip('/')}/api/v1/rbac/revoke"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    local_revoke_role(user, role)
    print({"user": user, "roles": sorted(list(local_list_roles(user)))})


@rbac_app.command("list")
def rbac_list(user: str, server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/rbac/user/{user}"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url)
            resp.raise_for_status()
            print(resp.json())
        return
    print({"user": user, "roles": sorted(list(local_list_roles(user)))})


@rbac_app.command("check")
def rbac_check(user: str, permission: str, server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/rbac/check"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url, params={"user": user, "permission": permission})
            resp.raise_for_status()
            print(resp.json())
        return
    print({
        "user": user,
        "permission": permission,
        "allowed": local_check_permission(user, permission),
    })


@invites_app.command("create")
def invites_create(org_id: str, email: str, role: str, server: str = typer.Option(None)):
    payload = {"org_id": org_id, "email": email, "role": role}
    if server:
        url = f"{server.rstrip('/')}/api/v1/invites"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    print(local_create_invite(org_id, email, role))


@invites_app.command("list")
def invites_list(org_id: str = typer.Option(None), server: str = typer.Option(None)):
    if server:
        params = {"org_id": org_id} if org_id else None
        url = f"{server.rstrip('/')}/api/v1/invites"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            print(resp.json())
        return
    print(local_list_invites(org_id))


@invites_app.command("accept")
def invites_accept(token: str, user_id: str, server: str = typer.Option(None)):
    payload = {"token": token, "user_id": user_id}
    if server:
        url = f"{server.rstrip('/')}/api/v1/invites/accept"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    print(local_accept_invite(token, user_id))


@pat_app.command("create")
def pat_create(user_id: str, label: str = typer.Option("cli"), server: str = typer.Option(None)):
    payload = {"user_id": user_id, "label": label}
    if server:
        url = f"{server.rstrip('/')}/api/v1/pat"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    print(local_create_pat(user_id, label))


@pat_app.command("list")
def pat_list(user_id: str, server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/pat"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url, params={"user_id": user_id})
            resp.raise_for_status()
            print(resp.json())
        return
    print(local_list_pat(user_id))


@pat_app.command("revoke")
def pat_revoke(token: str, server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/pat/revoke"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, params={"token": token})
            resp.raise_for_status()
            print(resp.json())
        return
    local_revoke_pat(token)
    print({"token": token, "revoked": True})


@catalog_app.command("add")
def catalog_add(
    item_id: str,
    name: str,
    asset_type: str = typer.Option("dataset", "--type"),
    domain: str | None = typer.Option(None),
    description: str = typer.Option(""),
    tags: str = typer.Option("", help="comma separated"),
    owner: str = typer.Option(None),
    sensitivity: str = typer.Option("internal"),
    field: list[str] = typer.Option([], "--field", help="field spec name:type[:description]"),
    server: str = typer.Option(None),
):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    field_entries = []
    for entry in field:
        parts = [p.strip() for p in entry.split(":", 2)]
        if len(parts) < 2:
            raise typer.BadParameter("field spec must follow name:type[:description]")
        field_payload = {"name": parts[0], "type": parts[1]}
        if len(parts) == 3 and parts[2]:
            field_payload["description"] = parts[2]
        field_entries.append(field_payload)
    payload = {
        "id": item_id,
        "name": name,
        "type": asset_type,
        "domain": domain,
        "description": description or None,
        "owner": owner,
        "sensitivity": sensitivity,
        "tags": tag_list,
        "fields": field_entries,
        "metadata": {},
    }
    if server:
        url = f"{server.rstrip('/')}/api/v1/catalog/items"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    item = CatalogItem(**payload)
    catalog_registry.add(item)
    print(item.model_dump(mode="json"))


@catalog_app.command("ls")
def catalog_list(
    asset_type: str | None = typer.Option(None, "--type"),
    domain: str | None = typer.Option(None),
    tag: str | None = typer.Option(None),
    sensitivity: str | None = typer.Option(None),
    server: str | None = typer.Option(None),
):
    if server:
        params = {
            key: value
            for key, value in {
                "type": asset_type,
                "domain": domain,
                "tag": tag,
                "sensitivity": sensitivity,
            }.items()
            if value
        }
        url = f"{server.rstrip('/')}/api/v1/catalog/assets"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            print(resp.json())
        return
    items = catalog_registry.list(asset_type=asset_type, domain=domain, tag=tag, sensitivity=sensitivity)
    print([item.model_dump(mode="json") for item in items])


@catalog_app.command("show")
def catalog_show(item_id: str, server: str = typer.Option(None)):
    if server:
        base = f"{server.rstrip('/')}"
        urls = [
            f"{base}/api/v1/catalog/datasets/{item_id}",
            f"{base}/api/v1/catalog/items/{item_id}",
        ]
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            for url in urls:
                resp = client.get(url)
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                print(resp.json())
                return
        raise typer.Exit(code=1)
    item = catalog_registry.get(item_id)
    if not item:
        print({"error": "not_found"})
    else:
        print(item.model_dump(mode="json"))


@connectors_app.command("list")
def connectors_list(server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/connectors"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url)
            resp.raise_for_status()
            print(resp.json())
        return
    print(connector_registry.list())


@connectors_app.command("test")
def connectors_test(name: str, params: str = typer.Option("{}"), server: str = typer.Option(None)):
    payload = {"name": name, "params": json.loads(params)}
    if server:
        url = f"{server.rstrip('/')}/api/v1/connectors/test"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    connector = connector_registry.create(name, **payload["params"])
    print({"sample": connector.fetch(limit=1)})


@pay_app.command("adapters")
def pay_adapters(server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/pay/adapters"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url)
            resp.raise_for_status()
            print(resp.json())
        return
    print(list(local_payments_adapters()))


@pay_app.command("intent", hidden=True)
def pay_intent(org: str, amount: int, currency: str = typer.Option("KRW"), customer_ref: str = typer.Option(None), adapter: str = typer.Option("manual_stub"), server: str = typer.Option(None)):
    payload = {
        "org_id": org,
        "amount": amount,
        "currency": currency,
        "customer_ref": customer_ref,
        "metadata": {},
        "adapter": adapter,
    }
    if server:
        url = f"{server.rstrip('/')}/api/v1/payments/intent"
        with httpx.Client(timeout=15, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    intent = _local_payments.create_intent(org_id=org, amount=amount, currency=currency, customer_ref=customer_ref, metadata={}, adapter_name=adapter)
    print(intent.model_dump(mode="json"))


@pay_app.command("confirm", hidden=True)
def pay_confirm(intent_id: str, payment_method: str, server: str = typer.Option(None)):
    payload = {"intent_id": intent_id, "payment_method": payment_method}
    if server:
        url = f"{server.rstrip('/')}/api/v1/payments/confirm"
        with httpx.Client(timeout=15, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    try:
        intent = _local_payments.confirm_intent(intent_id, payment_method)
    except KeyError:
        typer.echo("intent_not_found")
        raise typer.Exit(code=1)
    charge = _local_payments.latest_charge_for_intent(intent.id)
    print(
        {
            "intent": intent.model_dump(mode="json"),
            "charge": charge.model_dump(mode="json") if charge else None,
        }
    )


@pay_app.command("capture", hidden=True)
def pay_capture(charge_id: str, amount: int = typer.Option(None), server: str = typer.Option(None)):
    payload = {"charge_id": charge_id, "amount": amount}
    if server:
        url = f"{server.rstrip('/')}/api/v1/payments/capture"
        with httpx.Client(timeout=15, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    try:
        charge = _local_payments.capture_charge(charge_id, amount=amount)
    except KeyError:
        typer.echo("charge_not_found")
        raise typer.Exit(code=1)
    print(charge.model_dump(mode="json"))


@pay_app.command("charge")
def pay_charge_run(
    org: str = typer.Option(None, "--org"),
    amount: int = typer.Option(None, "--amount"),
    invoice: str = typer.Option(None, "--invoice-id"),
    currency: str = typer.Option("KRW", "--currency"),
    payment_token: str = typer.Option("tok_test", "--pm"),
    adapter: str = typer.Option("stripe_stub", "--adapter"),
    idempotency_key: str = typer.Option(None, "--idempotency-key"),
    server: str = typer.Option(None),
):
    if not invoice and (org is None or amount is None):
        raise typer.BadParameter("org and amount are required when invoice-id is not supplied")
    payload = {
        "org_id": org,
        "invoice_id": invoice,
        "amount": amount,
        "currency": currency,
        "payment_token": payment_token,
        "adapter": adapter,
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    key = idempotency_key or _idempotency_key("pay")
    if server:
        headers = _default_headers()
        headers["Idempotency-Key"] = key
        url = f"{server.rstrip('/')}/api/v1/pay/charge"
        with httpx.Client(timeout=20, headers=headers) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    result = gateway_service.charge(
        org_id=org,
        invoice_id=invoice,
        amount=amount,
        currency=currency,
        payment_method=payment_token,
        payment_intent_id=None,
        adapter=adapter,
        metadata={},
        idempotency_key=key,
    )
    print(json.dumps({"status": result.status, "intent": result.intent, "charge": result.charge, "receipt": result.receipt}, indent=2))


@pay_app.command("refund")
def pay_refund_run(
    charge_id: str,
    amount: int = typer.Option(None, "--amount"),
    reason: str = typer.Option(None, "--reason"),
    idempotency_key: str = typer.Option(None, "--idempotency-key"),
    server: str = typer.Option(None),
):
    payload = {"charge_id": charge_id, "amount": amount, "reason": reason}
    payload = {k: v for k, v in payload.items() if v is not None}
    key = idempotency_key or _idempotency_key("refund")
    if server:
        headers = _default_headers()
        headers["Idempotency-Key"] = key
        url = f"{server.rstrip('/')}/api/v1/pay/refund"
        with httpx.Client(timeout=15, headers=headers) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    try:
        result = gateway_service.refund(
            charge_id=charge_id,
            amount=amount,
            reason=reason,
            idempotency_key=key,
        )
    except KeyError:
        typer.echo("charge_not_found")
        raise typer.Exit(code=1)
    print(json.dumps({"status": result.status, "refund": result.refund}, indent=2))


@pay_app.command("dunning-run")
def pay_dunning_run(
    invoice_id: str,
    org: str = typer.Option(None, "--org"),
    schedule: list[str] = typer.Option([], "--schedule"),
    default_channel: str = typer.Option("email", "--channel"),
    idempotency_key: str = typer.Option(None, "--idempotency-key"),
    server: str = typer.Option(None),
):
    schedule_payload = [{"channel": default_channel, "eta": eta} for eta in schedule]
    key = idempotency_key or _idempotency_key("dunning")
    if server:
        headers = _default_headers()
        headers["Idempotency-Key"] = key
        url = f"{server.rstrip('/')}/api/v1/pay/dunning/run"
        payload = {"invoice_id": invoice_id, "org_id": org, "schedule": schedule_payload}
        with httpx.Client(timeout=20, headers=headers) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    record = local_mark_overdue(invoice_id, org_id=org)
    for item in schedule_payload:
        local_schedule_followup(invoice_id, item["channel"], item["eta"])
    print(record)


@pay_app.command("reconcile-report")
def pay_reconcile_report(server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/reconcile/status"
        with httpx.Client(timeout=15, headers=_default_headers()) as client:
            resp = client.get(url)
            resp.raise_for_status()
            print(resp.json())
        return
    print(local_reconcile_status())


@pay_app.command("receipt-issue")
def pay_receipt_issue(invoice_id: str, server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/receipt/issue"
        with httpx.Client(timeout=15, headers=_default_headers()) as client:
            resp = client.post(url, json={"invoice_id": invoice_id})
            resp.raise_for_status()
            print(resp.json())
        return
    invoice = INVOICES.get(invoice_id)
    if not invoice:
        typer.echo("invoice_not_found")
        raise typer.Exit(code=1)
    receipt = Receipt(
        charge_id=invoice_id,
        org_id=invoice.get("org_id", "unknown"),
        total=int(invoice.get("total", 0)),
        currency=invoice.get("currency", "KRW"),
        issued_at=datetime.now(timezone.utc),
        tax_amount=int(invoice.get("tax", 0)),
    )
    pdf_uri, json_uri = render_receipt_assets(receipt.model_dump(mode="json"))
    receipt.pdf_uri = pdf_uri
    receipt.json_uri = json_uri
    payments_service.repo.receipts[receipt.id] = receipt
    print({"receipt_id": receipt.id, "pdf_url": pdf_uri, "json_url": json_uri})


@pay_app.command("show-charge")
def pay_show_charge(charge_id: str, server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/payments/charges/{charge_id}"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url)
            resp.raise_for_status()
            print(resp.json())
        return
    try:
        charge = _local_payments.get_charge(charge_id)
    except KeyError:
        typer.echo("charge_not_found")
        raise typer.Exit(code=1)
    print(charge.model_dump(mode="json"))


@pay_app.command("show-receipt")
def pay_show_receipt(receipt_id: str, server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/payments/receipts/{receipt_id}"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url)
            resp.raise_for_status()
            print(resp.json())
        return
    try:
        receipt = _local_payments.get_receipt(receipt_id)
    except KeyError:
        typer.echo("receipt_not_found")
        raise typer.Exit(code=1)
    print(receipt.model_dump(mode="json"))


def _parse_docs(doc_entries: list[str]) -> list[KYCDocument]:
    documents: list[KYCDocument] = []
    for entry in doc_entries:
        if ":" in entry:
            doc_type, uri = entry.split(":", 1)
        else:
            doc_type, uri = "other", entry
        documents.append(KYCDocument(doc_type=doc_type, uri=uri))
    return documents


@kyc_app.command("submit")
def kyc_submit(org: str, applicant_type: str = typer.Option("business"), doc: list[str] = typer.Option([], "--doc"), risk_tier: str = typer.Option("low"), server: str = typer.Option(None)):
    docs_payload = _parse_docs(doc)
    payload = {
        "org_id": org,
        "type": applicant_type,
        "docs": [d.model_dump(mode="json") for d in docs_payload],
        "risk_tier": risk_tier,
    }
    if server:
        url = f"{server.rstrip('/')}/api/v1/kyc/submit"
        with httpx.Client(timeout=15, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    record = local_kyc_service.submit(org_id=org, applicant_type=applicant_type, documents=docs_payload, risk_tier=risk_tier)
    local_kyc_service.evaluate(org)
    print(record.model_dump(mode="json"))


@kyc_app.command("status")
def kyc_status(org: str, server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/kyc/status"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url, params={"org_id": org})
            resp.raise_for_status()

@ext_app.command("init")
def ext_init(path: Path = typer.Argument(Path("extension")), ext_type: str = typer.Option("decision"), runtime: str = typer.Option("python-3.11")):
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": path.name,
        "version": "0.1.0",
        "type": ext_type,
        "runtime": runtime,
        "permissions": ["data.read"],
        "resources": {"cpu_ms": 500, "mem_mb": 64, "tmp_mb": 8},
    }
    (path / "ext.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    sample = path / ("main.py" if runtime.startswith("python") else "index.js")
    sample.write_text("# hello from extension\n", encoding="utf-8")
    typer.echo({"created": str(path)})


@ext_app.command("pack")
def ext_pack(src: Path, output: Path = typer.Option(Path("dist/ext.tgz"))):
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as tar:
        tar.add(src, arcname=src.name)
    typer.echo({"artifact": str(output)})


@ext_app.command("sign")
def ext_sign(artifact: Path, secret: str = typer.Option(None)):
    signature = sign_artifact(artifact, secret.encode("utf-8") if secret else None)
    typer.echo(signature)


@ext_app.command("push")
def ext_push(ref: str, artifact: Path, name: str, version: str, channel: str = typer.Option("dev"), server: str = typer.Option(None)):
    metadata = {"name": name, "version": version, "channel": channel}
    record = Artifact(name=name, version=version, channel=channel, path=str(artifact.resolve()), metadata=metadata)
    ext_registry.push(ref, record)
    typer.echo({"status": "pushed", "ref": ref})


@ext_app.command("install")
def ext_install(
    ref: str,
    signature: str,
    org: str = typer.Option("demo-org"),
    manifest: Path = typer.Option(None, "--manifest"),
    server: str = typer.Option(None),
):
    manifest_payload = None
    if manifest and manifest.exists():
        manifest_payload = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    if server:
        url = f"{server.rstrip('/')}/api/v1/ext/install"
        payload = {"org_id": org, "artifact_ref": ref, "signature": signature, "manifest": manifest_payload}
        with httpx.Client(timeout=15, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            typer.echo(resp.json())
        return
    artifact = ext_registry.get(ref)
    if not verify_artifact_signature(Path(artifact.path), signature):
        raise typer.Exit(code=1)
    entry = {
        "ref": ref,
        "enabled": False,
        "metadata": artifact.metadata,
        "manifest": manifest_payload or artifact.metadata.get("manifest"),
    }
    _local_ext_installs.setdefault(org, []).append(entry)
    typer.echo({"status": "installed", "org": org})


@ext_app.command("enable")
def ext_enable(org: str, name: str, version: str, server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/ext/enable"
        payload = {"org_id": org, "name": name, "version": version}
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            typer.echo(resp.json())
        return
    installs = _local_ext_installs.get(org, [])
    for record in installs:
        meta = record.get("metadata", {})
        if meta.get("name") == name and meta.get("version") == version:
            record["enabled"] = True
            typer.echo({"status": "enabled"})
            return
    typer.echo({"error": "install_not_found"})


@ext_app.command("disable")
def ext_disable(org: str, name: str, server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/ext/disable"
        payload = {"org_id": org, "name": name}
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 404:
                typer.echo({"error": "extension_not_installed"})
                raise typer.Exit(code=1)
            resp.raise_for_status()
            typer.echo(resp.json())
        return
    installs = _local_ext_installs.get(org, [])
    for record in installs:
        meta = record.get("metadata", {})
        if meta.get("name") == name:
            record["enabled"] = False
            typer.echo({"status": "disabled"})
            return
    typer.echo({"error": "install_not_found"})


@ext_app.command("ls")
def ext_list(org: str = typer.Option("demo-org"), server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/ext/list"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url, params={"org_id": org})
            resp.raise_for_status()
            typer.echo(resp.json())
        return
    typer.echo(_local_ext_installs.get(org, []))


@webhooks_cli_app.command("add")
def webhook_add(event: str, url: str, secret: str = typer.Option("webhook-secret"), server: str = typer.Option(None)):
    if server:
        payload = {"event": event, "target_url": url, "secret": secret}
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(f"{server.rstrip('/')}/api/v1/webhooks/subscribe", json=payload)
            resp.raise_for_status()
            typer.echo(resp.json())
        return
    record = {"id": _idempotency_key("wh"), "event": event, "target_url": url, "secret": secret}
    _local_webhooks.append(record)
    typer.echo({"status": "added", "id": record["id"]})


@webhooks_cli_app.command("ls")
def webhook_ls(event: str = typer.Option(None), server: str = typer.Option(None)):
    if server:
        params = {"event": event} if event else None
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(f"{server.rstrip('/')}/api/v1/webhooks/subscribe", params=params)
            resp.raise_for_status()
            typer.echo(resp.json())
        return
    if event:
        typer.echo([record for record in _local_webhooks if record["event"] == event])
    else:
        typer.echo(_local_webhooks)


@webhooks_cli_app.command("rm")
def webhook_rm(subscription_id: str = typer.Argument(...), server: str = typer.Option(None)):
    if server:
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.delete(f"{server.rstrip('/')}/api/v1/webhooks/subscribe/{subscription_id}")
            if resp.status_code == 404:
                typer.echo({"error": "subscription_not_found"})
                raise typer.Exit(code=1)
            resp.raise_for_status()
            typer.echo({"removed": 1})
        return
    before = len(_local_webhooks)
    _local_webhooks[:] = [item for item in _local_webhooks if item["id"] != subscription_id]
    typer.echo({"removed": before - len(_local_webhooks)})


@market_app.command("ls")
def market_ls(channel: str = typer.Option("private-beta"), server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/marketplace/list"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url, params={"channel": channel})
            resp.raise_for_status()
            typer.echo(resp.json())
        return
    artifacts = ext_registry.list_channel(channel)
    typer.echo([artifact.__dict__ for artifact in artifacts])
            print(resp.json())
        return
    try:
        record = local_kyc_service.status(org)
    except KeyError:
        typer.echo("kyc_not_found")
        raise typer.Exit(code=1)
    print(record.model_dump(mode="json"))


@app.command("search")
def search_catalog(
    query: str,
    scope: str = typer.Option("asset"),
    limit: int = typer.Option(5),
    sensitivity: str | None = typer.Option(None),
    server: str = typer.Option(None),
):
    if server:
        url = f"{server.rstrip('/')}/api/v1/search"
        params = {"q": query, "limit": limit, "scope": scope}
        if sensitivity:
            params["sensitivity"] = sensitivity
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            print(resp.json())
        return
    allowed = [sensitivity] if sensitivity else None
    ids = catalog_search(query, limit=limit, scope=scope, allowed_sensitivity=allowed)
    results = []
    for item_id in ids:
        item = catalog_registry.get(item_id)
        if item:
            results.append(item.model_dump(mode="json"))
    print({"results": results})


@lineage_app.command("ingest")
def lineage_ingest_cmd(dataset: str, edges_path: Path, server: str = typer.Option(None)):
    edges_data = yaml.safe_load(edges_path.read_text(encoding="utf-8"))
    if not isinstance(edges_data, list):
        raise typer.BadParameter("edges file must contain a list of edges")
    if server:
        url = f"{server.rstrip('/')}/api/v1/lineage/edges"
        payload = {"dataset": dataset, "edges": edges_data}
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    edges = [LineageEdge.model_validate(edge) for edge in edges_data]
    lineage_ingest(dataset, edges)
    print({"dataset": dataset, "ingested": len(edges)})


@lineage_app.command("edges")
def lineage_edges(dataset: str, server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/lineage/edges/{dataset}"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url)
            resp.raise_for_status()
            print(resp.json())
        return
    edges = lineage_list_edges(dataset)
    print({"dataset": dataset, "edges": [edge.model_dump(mode=\"json\") for edge in edges]})


@lineage_app.command("graph")
def lineage_graph_cmd(dataset: str, depth: int = typer.Option(1), server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/lineage/graph"
        params = {"dataset": dataset, "depth": depth}
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            print(resp.json())
        return
    print(lineage_graph(dataset, depth=depth))


@lineage_app.command("impact")
def lineage_impact_cmd(
    dataset: str,
    field: str | None = typer.Option(None),
    depth: int = typer.Option(3),
    server: str = typer.Option(None),
):
    if server:
        url = f"{server.rstrip('/')}/api/v1/lineage/impact"
        params = {"dataset": dataset, "depth": depth}
        if field:
            params["field"] = field
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            print(resp.json())
        return
    print(lineage_impact(dataset, field=field, depth=depth))


@products_app.command("register")
def products_register(spec_path: Path, server: str = typer.Option(None)):
    spec_data = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    if server:
        url = f"{server.rstrip('/')}/api/v1/products/register"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=spec_data)
            resp.raise_for_status()
            print(resp.json())
        return
    spec = ProductSpec.model_validate(spec_data)
    version = product_registry.register(spec)
    print(version.model_dump(mode="json"))


@products_app.command("publish")
def products_publish(name: str, version: str, server: str = typer.Option(None)):
    payload = {"name": name, "version": version}
    if server:
        url = f"{server.rstrip('/')}/api/v1/products/publish"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    result = product_registry.publish(name, version)
    print(result.model_dump(mode="json"))


@products_app.command("rollback")
def products_rollback(name: str, version: str, server: str = typer.Option(None)):
    payload = {"name": name, "version": version}
    if server:
        url = f"{server.rstrip('/')}/api/v1/products/rollback"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    result = product_registry.rollback(name, version)
    print(result.model_dump(mode="json"))


@products_app.command("list")
def products_list(name: str = typer.Option(None), server: str = typer.Option(None)):
    if server:
        params = {"name": name} if name else None
        url = f"{server.rstrip('/')}/api/v1/products/list"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            print(resp.json())
        return
    items = product_registry.list(name=name)
    print({"products": [item.model_dump(mode="json") for item in items]})


@contracts_app.command("validate")
def contracts_validate(contract_path: Path, payload_path: Path, kind: str = typer.Option("input"), server: str = typer.Option(None)):
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    if server:
        url = f"{server.rstrip('/')}/api/v1/contracts/validate"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json={"contract_path": str(contract_path), "payload": payload, "kind": kind})
            resp.raise_for_status()
            print(resp.json())
        return
    contract = local_load_contract(contract_path)
    errors = local_validate_contract_payload(contract, payload, kind=kind)
    print({"valid": not errors, "errors": errors})


@contracts_app.command("compare")
def contracts_compare(base: str, target: str, server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/contracts/compare"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url, params={"base": base, "target": target})
            resp.raise_for_status()
            print(resp.json())
        return
    print(local_compare_versions(base, target))


@pipelines_app.command("run")
def pipelines_run(records_path: Path, server: str = typer.Option(None)):
    records = json.loads(records_path.read_text(encoding="utf-8"))
    if server:
        url = f"{server.rstrip('/')}/api/v1/pipelines/run"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json={"records": records})
            resp.raise_for_status()
            print(resp.json())
        return
    print({"records": local_run_pipeline(records)})


@quality_app.command("metrics")
def quality_metrics(records_path: Path, keys: str, server: str = typer.Option(None)):
    records = json.loads(records_path.read_text(encoding="utf-8"))
    key_list = [k.strip() for k in keys.split(",") if k.strip()]
    if server:
        url = f"{server.rstrip('/')}/api/v1/quality/metrics"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json={"records": records, "keys": key_list})
            resp.raise_for_status()
            print(resp.json())
        return
    print({"metrics": local_compute_quality(records, key_list)})
def _read_csv_rows(csv_path: Path) -> list[dict]:

    rows = list(csv.DictReader(csv_path.open("r", encoding="utf-8")))

    for r in rows:

        for k, v in list(r.items()):

            if isinstance(v, str) and v in ("True", "False"):

                r[k] = v == "True"

            else:

                try:

                    if isinstance(v, str) and "." in v:

                        r[k] = float(v)

                    else:

                        r[k] = int(v) if isinstance(v, str) else v

                except Exception:

                    pass

    return rows



def _default_headers() -> dict[str, str]:
    return {
        "X-Api-Key": settings.admin_api_key or "dev-key",
        "X-Role": "admin",
        "X-Tenant-ID": "demo-tenant",
    }


def _idempotency_key(prefix: str = "cli") -> str:
    return f"{prefix}-{uuid4().hex}"


def _pack_dirs() -> list[Path]:
    root = Path(__file__).resolve().parents[2]
    candidates = [
        Path(settings.data_dir) / "packs",
        root / "packages" / "packs",
    ]
    resolved: list[Path] = []
    for cand in candidates:
        target = cand if cand.is_absolute() else (root / cand)
        if target.exists() and target not in resolved:
            resolved.append(target)
    return resolved


def _iter_pack_files() -> list[Path]:
    files: list[Path] = []
    for directory in _pack_dirs():
        files.extend(list(directory.glob("*.yaml")))
        files.extend(list(directory.glob("*.yml")))
        files.extend(list(directory.glob("*.json")))
    return files


def _find_pack_file(name: str) -> Path:
    for path in _iter_pack_files():
        if path.stem == name:
            return path
    raise FileNotFoundError(f"pack not found: {name}")





@app.command()

def apply(

    contracts_dir: Path = typer.Option(Path("packages/contracts"), help="contracts dir"),

    rules_dir: Path = typer.Option(Path("packages/rules"), help="rules dir"),

    routes_file: Path = typer.Option(Path("packages/routes/model_routes.yaml"), help="routes file"),

):

    print("[bold green]Apply[/] (Lite): 파일 체크 및 린트 실행")

    for p in [contracts_dir, rules_dir, routes_file]:

        status = "OK" if p.exists() else "MISSING"

        print(f" - {p}: {status}")

    try:

        c = load_contract("lead_triage")

        print(f"lead_triage 계약 로드: rule_path={c.get('rule_path')}")

    except Exception as e:

        print(f"[yellow]계약 로드 실패: {e}")

    if rules_dir.exists():

        issues, coverage = lint_rules(rules_dir)

        if issues:

            print("[yellow]린트 이슈:")

            for i in issues:

                print(f" - [{i.kind}] {i.message} (rule={i.rule} other={i.other})")

        print(f"Coverage: {json.dumps(coverage, ensure_ascii=False)}")

    # 버전 매니페스트 생성/저장
    reg_dir = Path('var/registry')
    try:
        reg_dir.mkdir(parents=True, exist_ok=True)
        cm = _build_contracts_manifest(contracts_dir)
        rm = _build_rules_manifest(rules_dir)
        (reg_dir / 'contracts_manifest.json').write_text(json.dumps(cm, ensure_ascii=False, indent=2), encoding='utf-8')
        (reg_dir / 'rules_manifest.json').write_text(json.dumps(rm, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"Contracts version: {cm['version']}  Rules version: {rm['version']}")
    except Exception as ex:
        print(f"[yellow]매니페스트 생성 실패: {ex}")


@app.command()

def simulate(

    contract: str = typer.Argument(..., help="contract name"),

    csv_path: Path = typer.Argument(..., help="CSV with rows"),

    label_key: Optional[str] = typer.Option("converted", help="label column name"),

    server: Optional[str] = typer.Option(None, help="Gateway base URL; if omitted, run local"),

    html_out: Optional[Path] = typer.Option(None, help="Write HTML report to this path"),

    json_out: Optional[Path] = typer.Option(None, help="Write JSON metrics to this path"),

):

    """

    Run batch simulation and generate metrics reports.



    Generates both HTML and JSON reports showing precision, recall, and review rate metrics.

    """

    rows = _read_csv_rows(csv_path)

    if server:

        url = f"{server.rstrip('/')}/api/v1/simulate/{contract}"

        payload = {"rows": rows, "label_key": label_key}

        with httpx.Client(timeout=30) as client:

            resp = client.post(url, json=payload, headers={"Authorization": f"Bearer {settings.admin_api_key or 'secret-token'}"})

            resp.raise_for_status()

            result = resp.json()

            print(result)

    else:

        result = local_simulate(contract, rows, label_key)

        print(result)



    # Always attempt HTML + JSON report generation when local or when outputs provided

    try:

        html_path = html_out or Path("var/reports") / f"simulate_{contract}.html"

        json_path = json_out or Path("var/reports") / f"simulate_{contract}.json"

        tpl_path = Path("apps/rule_engine/templates/report.html")



        report_data = run_html_report(contract, csv_path, label_key, html_path, tpl_path, json_path)
        print(f"HTML report: {html_path}")
        print(f"JSON metrics: {json_path}")
        return



        print(f"[green]✓[/green] HTML report: {html_path}")

        print(f"[green]✓[/green] JSON metrics: {json_path}")

    except Exception as e:

        print(f"[yellow]Report generation skipped: {e}")





@app.command()

def replay(

    contract: str = typer.Argument(..., help="contract name"),

    csv_path: Path = typer.Argument(..., help="CSV with rows (org_id 포함)"),

):

    rows = _read_csv_rows(csv_path)

    results = []

    for row in rows:

        org_id = str(row.get("org_id", "replay"))

        payload = {k: v for k, v in row.items() if k != "org_id"}

        res = local_decide(contract, org_id, payload)

        results.append({"org_id": org_id, "decision_id": res["decision_id"], "class": res["class"], "reasons": res.get("reasons", [])})

    print(json.dumps({"count": len(results), "items": results}, ensure_ascii=False))





@audit_app.command("export")

def audit_export(out: Path = typer.Argument(Path("audit_export.jsonl"))):

    src = Path(settings.audit_log_path)

    if not src.exists():

        print("감사 원장 파일이 없습니다")

        raise typer.Exit(code=1)

    out.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"감사 원장 내보내기 완료: {out}")





# Backward-compatible alias

@app.command("audit-export")

def audit_export_alias(out: Path = typer.Argument(Path("audit_export.jsonl"))):

    return audit_export(out)


@seal_app.command("run")
def seal_run(
    csv_path: Path = typer.Option(Path("packages/samples/offline_eval.sample.csv"), help="CSV dataset"),
    out: Path = typer.Option(Path("var/reports/reality_seal.json"), help="Seal report JSON output"),
):
    """Reality-Seal KPI 리포트 생성(간이)"""
    try:
        from apps.seal.run import generate_seal_report
        rep = generate_seal_report(csv_path, out)
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"[red]seal run failed:[/] {e}")
        raise typer.Exit(code=1)


@seal_app.command("guard")
def seal_guard(strict: bool = typer.Option(False, help="엄격 모드: 리포트/룰 커버리지 등 강제")):
    """Reality-Seal 가드 실행(룰/감사/리포트)"""
    try:
        from apps.seal.guard import seal_check
        res = seal_check(strict=strict)
        ok = all(res.values())
        print(json.dumps({"ok": ok, **res}, ensure_ascii=False))
        if not ok:
            raise typer.Exit(code=2)
    except Exception as e:
        print(f"[red]seal guard failed:[/] {e}")
        raise typer.Exit(code=2)






def main():
    """dosctl 진입점"""
    app()


if __name__ == "__main__":
    main()


@consent_app.command("grant")
def consent_grant(
    subject_id: str,
    doc_hash: str,
    purpose: str = typer.Option(..., "--purpose", "-p"),
    scope: str = typer.Option("", help="Comma-separated scope entries"),
    server: str = typer.Option("http://localhost:8080"),
):
    url = f"{server.rstrip('/')}/api/v1/consent/grant"
    scope_list = [item.strip() for item in scope.split(",") if item.strip()]
    payload = {"subject_id": subject_id, "doc_hash": doc_hash, "purpose": purpose, "scope": scope_list}
    with httpx.Client(timeout=10) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        print(r.json())


@consent_app.command("revoke")
def consent_revoke(
    subject_id: str,
    doc_hash: str,
    purpose: str = typer.Option(None, "--purpose", "-p"),
    server: str = typer.Option("http://localhost:8080"),
):
    url = f"{server.rstrip('/')}/api/v1/consent/revoke"
    payload = {"subject_id": subject_id, "doc_hash": doc_hash}
    if purpose:
        payload["purpose"] = purpose
    with httpx.Client(timeout=10) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        print(r.json())


@consent_app.command("list")
def consent_list(subject_id: str, purpose: str = typer.Option(None, "--purpose", "-p"), server: str = typer.Option("http://localhost:8080")):
    url = f"{server.rstrip('/')}/api/v1/consent/list"
    params = {"subject_id": subject_id}
    if purpose:
        params["purpose"] = purpose
    with httpx.Client(timeout=10) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        print(r.json())


@boundary_app.command("check")
def boundary_check(
    dataset: str,
    org: str = typer.Option(..., "--org", "-o", help="Org identifier (region:slug)"),
    target_region: str = typer.Option(None, "--target", "-t"),
    purpose: str = typer.Option(None, "--purpose", "-p"),
    ticket_id: str = typer.Option(None, "--ticket"),
    retention_days: int = typer.Option(None, "--retention"),
    server: str = typer.Option("http://localhost:8080"),
):
    url = f"{server.rstrip('/')}/api/v1/boundaries/check"
    params = {"dataset": dataset, "org_id": org}
    if target_region:
        params["target_region"] = target_region
    if purpose:
        params["purpose"] = purpose
    if ticket_id:
        params["ticket_id"] = ticket_id
    if retention_days is not None:
        params["retention_days"] = retention_days
    with httpx.Client(timeout=10, headers=_default_headers()) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        print(resp.json())


@boundary_app.command("alerts")
def boundary_alerts(server: str = typer.Option("http://localhost:8080")):
    url = f"{server.rstrip('/')}/api/v1/boundaries/alerts"
    with httpx.Client(timeout=10, headers=_default_headers()) as client:
        resp = client.get(url)
        resp.raise_for_status()
        print(resp.json())


@metrics_app.command("show")
def metrics_show(server: str = typer.Option("http://localhost:8080")):
    url = f"{server.rstrip('/')}/api/v1/metrics"
    with httpx.Client(timeout=10) as client:
        r = client.get(url)
        r.raise_for_status()
        print(r.json())


@metrics_app.command("healthz")
def metrics_health(server: str = typer.Option("http://localhost:8080")):
    url = f"{server.rstrip('/')}/api/v1/metrics/healthz"
    with httpx.Client(timeout=10) as client:
        r = client.get(url)
        r.raise_for_status()
        print(r.json())

@app.command("health")
def health(server: str = typer.Option("http://localhost:8080")):
    """게이트웨이 헬스체크"""
    url = f"{server.rstrip('/')}/health"
    with httpx.Client(timeout=5) as client:
        r = client.get(url)
        r.raise_for_status()
        print(r.json())


ingest_app = typer.Typer(help="Ingest helpers")
app.add_typer(ingest_app, name="ingest")


@ingest_app.command("csv")
def ingest_csv_cmd(path: Path = typer.Argument(..., exists=True)):
    from apps.connectors.csv_ingest import ingest_csv as _ing
    import asyncio
    cnt = asyncio.run(_ing(path))
    print({"ingested": cnt})


@ingest_app.command("sheet")
def ingest_sheet_cmd(sheet_id: str, range_name: str = typer.Argument("A1:Z1000")):
    print({"ok": True, "sheet_id": sheet_id, "range": range_name, "note": "scaffold"})


@ingest_app.command("s3")
def ingest_s3_cmd(uri: str):
    print({"ok": True, "uri": uri, "note": "scaffold"})


billing_app = typer.Typer(help="Billing helpers")
app.add_typer(billing_app, name="billing")


@billing_app.command("preview")
def billing_preview(org: str, period: str, unit_price: float = 0.002, metric: str = "decision_calls", server: str = typer.Option("http://localhost:8080")):
    url = f"{server.rstrip('/')}/api/v1/billing/invoices/close"
    payload = {"org_id": org, "yyyymm": period, "unit_price": unit_price, "metric": metric}
    with httpx.Client(timeout=10) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        print(r.json())


@billing_app.command("show")
def billing_show(invoice_id: str, fmt: str = typer.Option("json"), server: str = typer.Option("http://localhost:8080")):
    url = f"{server.rstrip('/')}/api/v1/billing/invoices/{invoice_id}"
    with httpx.Client(timeout=10) as client:
        r = client.get(url, params={"fmt": fmt})
        r.raise_for_status()
        print(r.json())


@billing_app.command("ratebook")
def billing_ratebook(server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/billing/selfserve/ratebook"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url)
            resp.raise_for_status()
            print(resp.json())
        return
    ratebook_clear_cache()
    print(local_ratebook_plans())


@billing_app.command("rate")
def billing_rate(plan: str, metric: str = typer.Option("decision_calls"), server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/billing/selfserve/rate/{plan}/{metric}"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url)
            resp.raise_for_status()
            print(resp.json())
        return
    ratebook_clear_cache()
    print({"plan": plan, "metric": metric, "price": local_get_rate(plan, metric)})


@billing_app.command("prorate")
def billing_prorate(amount: float, used_days: int, total_days: int):
    print({"amount": amount, "prorated": local_prorate_amount(amount, used_days, total_days)})


@billing_app.command("subscribe")
def billing_subscribe(org_id: str, plan: str, server: str = typer.Option(None)):
    payload = {"org_id": org_id, "plan": plan}
    if server:
        url = f"{server.rstrip('/')}/api/v1/billing/selfserve/subscribe"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    print(local_self_subscribe(org_id, plan))


@billing_app.command("subscription")
def billing_subscription(org_id: str, server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/billing/selfserve/subscription/{org_id}"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url)
            resp.raise_for_status()
            print(resp.json())
        return
    record = local_get_subscription(org_id)
    print(record or {"org_id": org_id, "plan": None})


@billing_app.command("pay")
def billing_pay(invoice_id: str, amount: float, method: str = typer.Option("manual"), server: str = typer.Option(None)):
    payload = {"invoice_id": invoice_id, "amount": amount, "method": method}
    if server:
        url = f"{server.rstrip('/')}/api/v1/payments/record"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    print(local_record_payment(invoice_id, amount, method))


@billing_app.command("payments")
def billing_payments(invoice_id: str = typer.Option(None), server: str = typer.Option(None)):
    if server:
        params = {"invoice_id": invoice_id} if invoice_id else None
        url = f"{server.rstrip('/')}/api/v1/payments/ledger"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            print(resp.json())
        return
    print(local_list_payments(invoice_id))


@billing_app.command("dunning")
def billing_dunning(invoice_id: str, reason: str = typer.Option("unpaid"), channel: str = typer.Option("email"), eta: str = typer.Option(""), server: str = typer.Option(None)):
    payload = {"invoice_id": invoice_id, "reason": reason}
    if eta:
        payload["eta"] = eta
        payload["channel"] = channel
    if server:
        headers = _default_headers()
        headers["Idempotency-Key"] = _idempotency_key("dunning")
        url = f"{server.rstrip('/')}/api/v1/pay/dunning/run"
        with httpx.Client(timeout=10, headers=headers) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    record = local_mark_overdue(invoice_id, reason=reason)
    if eta:
        record = local_schedule_followup(invoice_id, channel, eta)
    print(record)


@billing_app.command("dunning-status")
def billing_dunning_status(invoice_id: str, server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/pay/dunning/{invoice_id}"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url)
            resp.raise_for_status()
            print(resp.json())
        return
    print(local_dunning_status(invoice_id))


@billing_app.command("reconcile")
def billing_reconcile(invoice_id: str, payment_id: str, amount: float, server: str = typer.Option(None)):
    payload = {"invoice_id": invoice_id, "payment_id": payment_id, "amount": amount}
    if server:
        url = f"{server.rstrip('/')}/api/v1/payments/reconcile"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            print(resp.json())
        return
    print(local_reconcile_invoice(invoice_id, payment_id, amount))


@billing_app.command("reconcile-status")
def billing_reconcile_status(invoice_id: str, server: str = typer.Option(None)):
    if server:
        url = f"{server.rstrip('/')}/api/v1/payments/reconcile/{invoice_id}"
        with httpx.Client(timeout=10, headers=_default_headers()) as client:
            resp = client.get(url)
            if resp.status_code == 404:
                print({"invoice_id": invoice_id, "status": "pending"})
                return
            resp.raise_for_status()
            print(resp.json())
        return
    print(local_get_reconciliation(invoice_id))

region_app = typer.Typer(help="Region ops")
app.add_typer(region_app, name="region")


@region_app.command("status")
def region_status(server: str = typer.Option("http://localhost:8080")):
    url = f"{server.rstrip('/')}/api/v1/region/status"
    with httpx.Client(timeout=5) as client:
        r = client.get(url)
        r.raise_for_status()
        print(r.json())


@region_app.command("promote")
def region_promote(to: str, server: str = typer.Option("http://localhost:8080")):
    url = f"{server.rstrip('/')}/api/v1/region/promote"
    with httpx.Client(timeout=5) as client:
        r = client.post(url, params={"to": to})
        r.raise_for_status()
        print(r.json())

failover_app = typer.Typer(help="Failover ops")
app.add_typer(failover_app, name="failover")


@failover_app.command("auto")
def failover_auto(force: bool = typer.Option(False), server: str = typer.Option("http://localhost:8080")):
    url = f"{server.rstrip('/')}/api/v1/failover/auto"
    with httpx.Client(timeout=10) as client:
        r = client.post(url, params={"force": str(force).lower()})
        r.raise_for_status()
        print(r.json())


health_app = typer.Typer(help="Health ops")
app.add_typer(health_app, name="health")


@health_app.command("ready")
def health_ready(server: str = typer.Option("http://localhost:8080")):
    url = f"{server.rstrip('/')}/api/v1/health/ready"
    with httpx.Client(timeout=5) as client:
        print(client.get(url).json())


@health_app.command("degrade")
def health_degrade(mode: str = typer.Argument("on"), server: str = typer.Option("http://localhost:8080")):
    url = f"{server.rstrip('/')}/api/v1/health/degrade/{mode}"
    with httpx.Client(timeout=5) as client:
        print(client.post(url).json())

admin_app = typer.Typer(help="Admin ops")
app.add_typer(admin_app, name="admin")


@admin_app.command("metrics")
def admin_metrics(org: str = typer.Option(None), period: str = typer.Option(None), server: str = typer.Option("http://localhost:8080"), corr_id: str = typer.Option(None)):
    url = f"{server.rstrip('/')}/api/v1/admin/metrics"
    headers = {}
    if corr_id:
        headers["X-Corr-Id"] = corr_id
    with httpx.Client(timeout=10, headers=headers) as client:
        r = client.get(url, params={"org_id": org, "period": period})
        r.raise_for_status()
        print(r.json())

policy_app = typer.Typer(help="Policy ops")
app.add_typer(policy_app, name="policy")


@policy_app.command("validate")
def policy_validate(bundle_file: Path):
    """Locally parse a bundle and report syntax issues without installing it."""
    from apps.policy.parser import parse_policy

    text = bundle_file.read_text(encoding="utf-8")
    blocks = [block.strip() for block in text.split("---") if block.strip()]
    errors: list[tuple[int, str]] = []
    for idx, block in enumerate(blocks, start=1):
        try:
            parse_policy(block)
        except Exception as exc:  # pragma: no cover - CLI helper
            errors.append((idx, str(exc)))
    if errors:
        for idx, message in errors:
            typer.secho(f"[block {idx}] {message}", fg="red")
        raise typer.Exit(code=1)
    typer.secho(f"Validated {len(blocks)} policy blocks", fg="green")


@policy_app.command("simulate")
def policy_simulate(bundle_file: Path, cases_file: Path):
    """Apply a bundle temporarily and evaluate each case locally."""
    import copy
    import json

    from apps.policy.store import STORE
    from apps.policy.pdp import evaluate

    bundle_text = bundle_file.read_text(encoding="utf-8")
    cases = json.loads(cases_file.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        raise typer.BadParameter("cases_file must contain a JSON list of evaluation payloads")

    backup = copy.deepcopy(STORE.list_policies())
    try:
        STORE.apply_bundle(
            "cli-simulate",
            bundle_text,
            metadata={"version": "v0.0.0", "approved_by": "dosctl"},
        )
        results = []
        for payload in cases:
            subject = payload.get("subject", {})
            action = payload.get("action")
            resource = payload.get("resource", {})
            context = payload.get("context", {})
            if not action:
                raise typer.BadParameter("each case requires an 'action'")
            decision = evaluate(subject, action, resource, context)
            results.append({"case": payload, "decision": decision.__dict__})
        typer.secho(json.dumps(results, indent=2), fg="cyan")
    finally:
        STORE._policies = backup  # type: ignore[attr-defined]


@policy_app.command("apply")
def policy_apply(
    name: str,
    bundle_file: Path,
    version: str = typer.Option(..., "--version", "-v"),
    approved_by: str = typer.Option(..., "--approved-by", "-a"),
    summary: str = typer.Option("", "--summary", "-s"),
    server: str = typer.Option("http://localhost:8080"),
):
    bundle_text = bundle_file.read_text(encoding="utf-8")
    payload = {
        "name": name,
        "bundle": bundle_text,
        "version": version,
        "approved_by": approved_by,
        "summary": summary or None,
    }
    url = f"{server.rstrip('/')}/api/v1/policies/install"
    with httpx.Client(timeout=15, headers=_default_headers()) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        print(resp.json())


@policy_app.command("eval")
def policy_eval(payload_file: Path, server: str = typer.Option("http://localhost:8080")):
    import json

    body = json.loads(payload_file.read_text(encoding="utf-8"))
    url = f"{server.rstrip('/')}/api/v1/policies/eval"
    with httpx.Client(timeout=10, headers=_default_headers()) as client:
        resp = client.post(url, json=body)
        resp.raise_for_status()
        print(resp.json())


@policy_app.command("list")
def policy_list(server: str = typer.Option("http://localhost:8080")):
    url = f"{server.rstrip('/')}/api/v1/policies/list"
    with httpx.Client(timeout=10, headers=_default_headers()) as client:
        resp = client.get(url)
        resp.raise_for_status()
        print(resp.json())


vault_app = typer.Typer(help="Vault ops")
app.add_typer(vault_app, name="vault")


@vault_app.command("set")
def vault_set(key: str, value: str):
    import httpx
    with httpx.Client(timeout=10) as client:
        r = client.post('http://localhost:8080/api/v1/vault/set', json={"key": key, "value": value})
        r.raise_for_status()
        print(r.json())


@vault_app.command("get")
def vault_get(key: str):
    import httpx
    with httpx.Client(timeout=10) as client:
        r = client.get('http://localhost:8080/api/v1/vault/get', params={"key": key})
        r.raise_for_status()
        print(r.json())
