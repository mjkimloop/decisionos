from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.auth.oidc import provider_singleton, generate_state, generate_code
from apps.auth.session import create_session, get_session, invalidate_session
from apps.auth.jwks import get_jwks


router = APIRouter(prefix="/api/v1/auth/oidc", tags=["auth"])


@router.get("/config")
def config_ep():
    return {
        "issuer": provider_singleton.issuer,
        "authorize_url": provider_singleton.build_authorize_url(generate_state()),
        "client_id": provider_singleton.client_id,
        "redirect_uri": provider_singleton.redirect_uri,
    }


class CallbackBody(BaseModel):
    code: str
    state: str


@router.post("/callback")
def callback_ep(payload: CallbackBody):
    tokens = provider_singleton.exchange_code(payload.code, payload.state)
    userinfo = provider_singleton.build_userinfo(tokens["access_token"])
    session = create_session(userinfo["sub"])
    return {
        "session_id": session.session_id,
        "userinfo": userinfo,
        "tokens": tokens,
    }


@router.get("/session/{session_id}")
def session_ep(session_id: str):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="session expired")
    return {
        "session_id": sess.session_id,
        "subject": sess.subject,
        "expires_at": sess.expires_at,
    }


@router.delete("/session/{session_id}")
def logout_ep(session_id: str):
    invalidate_session(session_id)
    return {"ok": True}


@router.get("/jwks")
def jwks_ep():
    return get_jwks()
