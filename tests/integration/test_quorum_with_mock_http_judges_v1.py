import json
import os

import pytest
from aiohttp import web

pytestmark = [pytest.mark.gate_aj]

from apps.judge.pool import quorum_decide
from apps.judge.providers.http import HTTPJudgeProvider
from apps.judge.providers.local import LocalJudgeProvider
from apps.judge.replay_plugins import SQLiteReplayStore
from apps.judge.crypto import hmac_sign_canonical


async def _judge_handler(request):
    key = os.environ.get("DECISIONOS_JUDGE_HMAC_KEY", "changeme")
    key_id = request.headers.get("X-Key-Id", "k1")
    sig = request.headers.get("X-DecisionOS-Signature")
    nonce = request.headers.get("X-DecisionOS-Nonce")
    ts = int(request.headers.get("X-DecisionOS-Timestamp", "0"))

    body = await request.read()
    payload = json.loads(body.decode("utf-8"))
    expected = hmac_sign_canonical(payload, key)
    if sig != expected:
        return web.Response(status=401)

    store: SQLiteReplayStore = request.app["store"]
    if store.seen_or_insert(key_id, nonce, ts):
        return web.Response(status=401)

    budget_level = payload["evidence"].get("budget", {}).get("level", "ok")
    decision = "pass" if budget_level == "ok" else "fail"
    return web.json_response({"decision": decision, "reasons": [], "version": "mock-1"})


@pytest.mark.asyncio
async def test_http_quorum_pass(monkeypatch, aiohttp_client):
    monkeypatch.setenv("DECISIONOS_JUDGE_HMAC_KEY", "integration-key")

    app = web.Application()
    app["store"] = SQLiteReplayStore(":memory:")
    app.router.add_post("/judge", _judge_handler)
    client = await aiohttp_client(app)
    url = str(client.make_url("/judge"))

    evidence = {"budget": {"level": "ok"}, "integrity": {"signature_sha256": "x"}}
    slo = {"quorum": {"fail_closed_on_degrade": True}}

    providers = [
        LocalJudgeProvider("local-a"),
        HTTPJudgeProvider("http-b", url, timeout_ms=1500, require_signature=True),
        HTTPJudgeProvider("http-c", url, timeout_ms=1500, require_signature=True),
    ]

    res = await quorum_decide(providers, evidence, slo, k=2, n=3, fail_closed_on_degrade=True)
    assert res["final"] == "pass"
    assert len(res["votes"]) == 3


@pytest.mark.asyncio
async def test_http_replay_rejected(monkeypatch, aiohttp_client):
    monkeypatch.setenv("DECISIONOS_JUDGE_HMAC_KEY", "integration-key")

    app = web.Application()
    app["store"] = SQLiteReplayStore(":memory:")
    app.router.add_post("/judge", _judge_handler)
    client = await aiohttp_client(app)
    url = str(client.make_url("/judge"))

    evidence = {"budget": {"level": "ok"}, "integrity": {"signature_sha256": "x"}}
    slo = {"quorum": {"fail_closed_on_degrade": True}}

    # 모든 HTTP 요청이 동일 nonce를 사용하도록 패치 → 두 번째 요청부터 401
    monkeypatch.setattr("apps.judge.providers.http.secrets.token_hex", lambda _: "deadbeef" * 4)

    providers = [
        HTTPJudgeProvider("http-b", url, timeout_ms=1500, require_signature=True),
        HTTPJudgeProvider("http-c", url, timeout_ms=1500, require_signature=True),
    ]

    res = await quorum_decide(providers, evidence, slo, k=2, n=2, fail_closed_on_degrade=True)
    assert res["final"] == "fail"
    assert res["degraded"] is True
