import asyncio

import pytest

pytestmark = [pytest.mark.gate_aj]

from apps.judge.errors import JudgeTimeout
from apps.judge.pool import quorum_decide
from apps.judge.providers.base import JudgeProvider


class _StubProvider(JudgeProvider):
    def __init__(self, provider_id: str, decision: str, latency: float = 0.0):
        super().__init__(provider_id)
        self._decision = decision
        self._latency = latency

    async def evaluate(self, evidence, slo):
        if self._latency:
            await asyncio.sleep(self._latency)
        return {"decision": self._decision, "reasons": [], "meta": {"latency_ms": self._latency * 1000}, "id": self.provider_id}


class _ErrorProvider(JudgeProvider):
    def __init__(self, provider_id: str):
        super().__init__(provider_id)

    async def evaluate(self, evidence, slo):
        raise JudgeTimeout("timeout")


@pytest.mark.asyncio
async def test_quorum_pass_with_mixed_votes():
    evidence = {"integrity": {"signature_sha256": "x"}}
    slo = {"quorum": {"fail_closed_on_degrade": True}}
    providers = [
        _StubProvider("p1", "pass"),
        _StubProvider("p2", "pass"),
        _StubProvider("p3", "fail"),
    ]

    res = await quorum_decide(providers, evidence, slo, k=2, n=3, fail_closed_on_degrade=True)
    assert res["final"] == "pass"
    assert res["pass_count"] == 2
    assert len(res["votes"]) == 3


@pytest.mark.asyncio
async def test_quorum_fail_when_degraded_and_fail_closed():
    evidence = {"integrity": {"signature_sha256": "x"}}
    slo = {"quorum": {"fail_closed_on_degrade": True}}
    providers = [
        _StubProvider("p1", "pass"),
        _StubProvider("p2", "pass"),
        _ErrorProvider("p3"),
    ]

    res = await quorum_decide(providers, evidence, slo, k=2, n=3, fail_closed_on_degrade=True)
    assert res["final"] == "fail"  # degrade → fail-closed
    assert res["degraded"] is True
    assert len(res["votes"]) == 3


@pytest.mark.asyncio
async def test_quorum_pass_when_fail_closed_disabled():
    evidence = {"integrity": {"signature_sha256": "x"}}
    slo = {}
    providers = [
        _StubProvider("p1", "pass"),
        _StubProvider("p2", "pass"),
        _ErrorProvider("p3"),
    ]

    res = await quorum_decide(providers, evidence, slo, k=2, n=3, fail_closed_on_degrade=False)
    assert res["final"] == "pass"
    assert res["degraded"] is True
