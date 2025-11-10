from __future__ import annotations

from typing import Any, Dict

from sdk.python.decorators import pre_hook, post_hook, with_context


@pre_hook
def add_feature(config: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    ctx.setdefault("features", {})["risk_score"] = 0.42
    return ctx["request"]


@post_hook
def annotate_response(response: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    response.setdefault("extensions", {})["risk_score"] = ctx["features"]["risk_score"]
    return response


@with_context
def handle(config: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "ok", "config": config, "trace_id": ctx.get("trace_id")}
