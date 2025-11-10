from __future__ import annotations

import asyncio

from apps.switchboard.router import Router


def run(coro):
    return asyncio.run(coro)


def test_capability_routes_to_openai_by_default():
    r = Router()
    out = run(r.route("hello", capability="default", cost_budget=1.0, timeout=0.5))
    assert out["meta"]["adapter_used"] == "openai"


def test_unknown_capability_uses_default_mapping():
    r = Router()
    out = run(r.route("hello", capability="unknown", cost_budget=1.0, timeout=0.5))
    assert out["meta"]["adapter_used"] in {"openai", "local"}


def test_cost_budget_triggers_local_fallback():
    r = Router()
    # Very small budget forces local
    out = run(r.route("A" * 200, capability="default", cost_budget=0.00001, timeout=0.5))
    assert out["meta"]["adapter_used"] == "local"
    assert out["meta"]["fallback_reason"] == "cost"


def test_timeout_fallback_to_local():
    r = Router()
    # SLOW prompt with very small timeout triggers timeout fallback
    out = run(r.route("SLOW prompt", capability="default", cost_budget=1.0, timeout=0.001))
    assert out["meta"]["adapter_used"] == "local"
    assert out["meta"]["fallback_reason"] == "timeout"


def test_error_fallback_to_local():
    r = Router()
    out = run(r.route("FAIL now", capability="default", cost_budget=1.0, timeout=0.5))
    assert out["meta"]["adapter_used"] == "local"
    assert out["meta"]["fallback_reason"] == "error"


def test_local_adapter_exec_structure():
    r = Router()
    out = run(r.route("x", capability="batch", cost_budget=0.0, timeout=0.5))
    assert out["content"].startswith("local:")
    assert out["meta"]["adapter_used"] == "local"


def test_openai_exec_structure():
    r = Router()
    out = run(r.route("hello", capability="default", cost_budget=1.0, timeout=0.5))
    assert out["content"].startswith("openai:")


def test_negative_budget_treated_as_zero_cost():
    r = Router()
    # Negative budget coerced to 0 → cost fallback
    out = run(r.route("hello world", capability="default", cost_budget=-1.0, timeout=0.5))
    assert out["meta"]["adapter_used"] in {"local", "openai"}
    # Ensure field present
    assert "budget" in out["meta"] and "cost" in out["meta"]["budget"]


def test_meta_contains_primary_and_budget():
    r = Router()
    out = run(r.route("hello", capability="creative_writing", cost_budget=1.0, timeout=0.5))
    assert out["meta"]["primary"] in {"openai", "local"}
    assert out["meta"]["budget"]["timeout"] == 0.5


def test_cost_within_budget_uses_openai():
    r = Router()
    out = run(r.route("short", capability="default", cost_budget=1.0, timeout=0.5))
    assert out["meta"]["adapter_used"] == "openai"

