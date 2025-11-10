import pytest

from apps.policy.pdp import evaluate
from apps.policy.store import STORE


@pytest.fixture(autouse=True)
def _reset_store():
    STORE.clear()
    yield
    STORE.clear()


DEFAULT_META = {"version": "v0.0.1", "approved_by": "tester"}


def apply_simple_bundle(name: str, bundle: str, meta: dict | None = None) -> None:
    STORE.apply_bundle(name, bundle, metadata=meta or DEFAULT_META)


def test_explicit_deny_overrides_allow():
    bundle = """
deny(read, subject, resource) meta {
    id: "deny-restricted"
    priority: 10
}
when { "restricted" in resource.get("tags", []) }
---
permit(read, subject, resource) meta {
    id: "allow-viewer"
    priority: 5
}
when { subject.get("role") == "viewer" }
    """
    apply_simple_bundle("default", bundle)

    decision = evaluate(
        subject={"role": "viewer"},
        action="read",
        resource={"tags": ["restricted"]},
        context={"tenant": "t1"},
    )

    assert not decision.allow
    assert decision.effect == "deny"
    assert decision.reason == "explicit_deny"
    assert decision.policy_id == "deny-restricted"
    assert decision.trace and decision.trace[0].matched is True
    assert decision.trace[0].metadata["version"] == "v0.0.1"


def test_allow_when_no_deny_matches():
    bundle = """
permit(read, subject, resource) meta {
    id: "allow-viewer"
    priority: 5
}
when { subject.get("role") == "viewer" }
    """
    apply_simple_bundle("default", bundle)

    decision = evaluate(
        subject={"role": "viewer"},
        action="read",
        resource={"tags": []},
        context={"tenant": "t1"},
    )

    assert decision.allow
    assert decision.effect == "allow"
    assert decision.policy_id == "allow-viewer"
    assert decision.trace[0].metadata["approved_by"] == "tester"


def test_deny_by_default_when_no_policy_matches():
    decision = evaluate(
        subject={"role": "guest"},
        action="read",
        resource={"tags": []},
        context={"tenant": "t1"},
    )

    assert not decision.allow
    assert decision.reason == "deny_by_default"


def test_unless_clause_blocks_match():
    bundle = """
permit(read, subject, resource) meta {
    id: "allow-nonprod"
    priority: 3
}
when { resource.get("environment") == "nonprod" }
unless { context.get("break_glass") is True }
    """
    apply_simple_bundle("default", bundle)

    decision = evaluate(
        subject={"role": "viewer"},
        action="read",
        resource={"environment": "nonprod"},
        context={"tenant": "t1", "break_glass": True},
    )

    assert not decision.allow
    assert decision.reason == "deny_by_default"
    assert decision.trace[-1].unless_result is True
