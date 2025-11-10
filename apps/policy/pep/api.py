from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Callable, Dict

from fastapi import HTTPException, Request

from ..pdp import evaluate

logger = logging.getLogger(__name__)


def enforcement_callable(get_subject: Callable[[Request], dict], get_resource: Callable[[Request], dict]):
    async def dependency(request: Request):
        subject = get_subject(request)
        resource = get_resource(request)
        context: Dict[str, object] = {
            "tenant": request.headers.get("X-Tenant-ID"),
            "path": request.url.path,
            "method": request.method.lower(),
            "client_ip": request.client.host if request.client else None,
            "headers": {k: v for k, v in request.headers.items() if k.lower().startswith("x-")},
        }
        decision = evaluate(subject, request.method.lower(), resource, context)
        request.state.policy_decision = decision  # type: ignore[attr-defined]
        if not decision.allow:
            detail = {
                "error": "policy_denied",
                "reason": decision.reason or "denied",
                "policy_id": decision.policy_id,
                "bundle": decision.bundle,
                "purpose": decision.purpose,
            }
            logger.warning(
                "policy_denied",
                extra={
                    "policy_decision": detail,
                    "trace": [asdict(trace) for trace in decision.trace],
                },
            )
            raise HTTPException(status_code=403, detail=detail)
    return dependency


__all__ = ["enforcement_callable"]
