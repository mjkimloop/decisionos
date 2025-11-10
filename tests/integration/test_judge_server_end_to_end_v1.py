import json
import hashlib
import time

import asyncio
import httpx
import pytest

pytestmark = [pytest.mark.gate_aj]

from apps.judge.server import create_app
from apps.judge.crypto import hmac_sign


def _payload():
    evidence = {
        "meta": {"tenant": "demo"},
        "witness": {"csv_sha256": "abc"},
        "usage": {},
        "rating": {},
        "quota": {},
        "budget": {"level": "ok", "spent": 0.1, "limit": 1.0},
        "anomaly": {"is_spike": False},
        "perf": None,
        "perf_judge": {
            "latency_ms": {"p50": 100, "p95": 800, "p99": 1200},
            "availability": 0.999,
            "error_rate": 0.001,
            "signature_error_rate": 0.0001,
        },
        "integrity": {"signature_sha256": "deadbeef"},
    }
    core = {
        k: evidence[k]
        for k in ["meta", "witness", "usage", "rating", "quota", "budget", "anomaly"]
    }
    evidence["integrity"]["signature_sha256"] = hashlib_sha(core)
    slo = {
        "judge_infra": {
            "latency": {"max_p95_ms": 900, "max_p99_ms": 1500},
            "availability": {"min_availability": 0.99},
            "sig": {"max_sig_error_rate": 0.001},
        }
    }
    return {"evidence": evidence, "slo": slo}


def hashlib_sha(core: dict) -> str:
    return hashlib.sha256(json.dumps(core, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def test_judge_server_signature_and_metrics(monkeypatch):
    monkeypatch.setenv("DECISIONOS_JUDGE_KEYS", '[{"key_id":"k1","secret":"super-secret","state":"active"}]')
    monkeypatch.setenv("DECISIONOS_REPLAY_SQLITE", ":memory:")
    app = create_app()

    async def _run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            payload = _payload()
            headers = _signed_headers(payload, "k1")
            res = await client.post("/judge", json=payload, headers=headers)
            assert res.status_code == 200
            assert res.json()["decision"] == "pass"

            bad_headers = headers.copy()
            bad_headers["X-DecisionOS-Signature"] = "bad"
            res2 = await client.post("/judge", json=payload, headers=bad_headers)
            assert res2.status_code == 401

            res3 = await client.post("/judge", json=payload, headers=headers)
            assert res3.status_code == 401

            metrics = (await client.get("/metrics")).json()
            assert metrics["count"] >= 2
            assert "latency_ms" in metrics

    asyncio.run(_run())


def _signed_headers(payload: dict, kid: str) -> dict:
    signature = hmac_sign(payload, b"super-secret")
    return {
        "X-Key-Id": kid,
        "X-DecisionOS-Signature": signature,
        "X-DecisionOS-Nonce": "n-" + str(int(time.time())),
        "X-DecisionOS-Timestamp": str(int(time.time())),
    }
