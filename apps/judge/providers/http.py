from __future__ import annotations

import asyncio
import secrets
import time
from typing import Any, Callable, Dict, Optional

import httpx

from .base import JudgeProvider
from apps.judge.crypto import MultiKeyLoader, hmac_sign
from apps.judge.errors import JudgeBadSignature, JudgeHTTPError, JudgeTimeout


class HTTPJudgeProvider(JudgeProvider):
    """
    원격 HTTP 저지를 호출하는 Provider.
    - 요청마다 nonce/timestamp/HMAC 서명 적용
    - timeout/retry + 간단 circuit-breaker 지원
    """

    def __init__(
        self,
        provider_id: str,
        url: str,
        *,
        timeout_ms: int = 2000,
        retries: int = 2,
        require_signature: bool = True,
        key_id: Optional[str] = None,
        breaker_max_failures: int = 3,
        breaker_reset_seconds: float = 5.0,
        verify_ssl: bool = True,
        client_factory: Optional[Callable[[], httpx.AsyncClient]] = None,
    ) -> None:
        super().__init__(provider_id)
        self.url = url
        self.timeout = timeout_ms / 1000
        self.retries = retries
        self.require_signature = require_signature
        self.key_id = key_id or "k1"
        self._breaker_max_failures = breaker_max_failures
        self._breaker_reset_seconds = breaker_reset_seconds
        self._breaker_open_until: Optional[float] = None
        self._failure_count = 0
        self._verify_ssl = verify_ssl
        self._client_factory = client_factory or (
            lambda: httpx.AsyncClient(timeout=self.timeout, verify=self._verify_ssl)
        )
        self._key_loader = MultiKeyLoader()

    def _circuit_open(self) -> bool:
        if self._breaker_open_until is None:
            return False
        if time.time() >= self._breaker_open_until:
            self._breaker_open_until = None
            self._failure_count = 0
            return False
        return True

    def _register_failure(self) -> None:
        self._failure_count += 1
        if self._failure_count >= self._breaker_max_failures:
            self._breaker_open_until = time.time() + self._breaker_reset_seconds

    def _reset_breaker(self) -> None:
        self._failure_count = 0
        self._breaker_open_until = None

    def _build_headers(self, payload: Dict[str, Any]) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "X-DecisionOS-Nonce": payload["nonce"],
            "X-DecisionOS-Timestamp": str(payload["ts"]),
        }
        if self.require_signature:
            km = self._key_loader.get(self.key_id) or self._key_loader.choose_active()
            if not km:
                raise JudgeBadSignature("no signing key available")
            headers["X-DecisionOS-Signature"] = hmac_sign(payload, km.secret)
            headers["X-Key-Id"] = km.key_id
        return headers

    async def evaluate(self, evidence: Dict[str, Any], slo: Dict[str, Any]) -> Dict[str, Any]:
        if self._circuit_open():
            raise JudgeHTTPError(503, f"circuit open for provider {self.provider_id}")

        attempt = 0
        delay = 0.2
        last_exc: Optional[Exception] = None

        while attempt <= self.retries:
            attempt += 1
            client = self._client_factory()
            try:
                async with client:
                    start = time.perf_counter()
                    payload = {
                        "evidence": evidence,
                        "slo": slo,
                        "ts": int(time.time()),
                        "nonce": secrets.token_hex(16),
                    }
                    headers = self._build_headers(payload)

                    response = await client.post(self.url, json=payload, headers=headers)
                    if response.status_code == 401:
                        raise JudgeBadSignature("remote judge rejected signature/nonce")
                    if response.status_code >= 500:
                        raise JudgeHTTPError(response.status_code)
                    if response.status_code >= 400:
                        raise JudgeHTTPError(response.status_code, "remote judge rejected request")

                    data = response.json()
                    latency_ms = (time.perf_counter() - start) * 1000
                    vote = {
                        "decision": data.get("decision"),
                        "reasons": data.get("reasons", []),
                        "meta": data.get("meta", {}),
                        "version": data.get("version"),
                        "id": self.provider_id,
                    }
                    vote["meta"].setdefault("latency_ms", round(latency_ms, 2))
                    self._reset_breaker()
                    return vote
            except httpx.TimeoutException as exc:
                last_exc = JudgeTimeout(str(exc))
                self._register_failure()
            except JudgeBadSignature as exc:
                last_exc = exc
                self._register_failure()
                break
            except JudgeHTTPError as exc:
                last_exc = exc
                if exc.status_code >= 500:
                    self._register_failure()
                else:
                    break
            except httpx.RequestError as exc:
                last_exc = exc
                self._register_failure()
            finally:
                if attempt <= self.retries:
                    await asyncio.sleep(delay)
                    delay *= 3

        assert last_exc is not None
        raise last_exc


__all__ = ["HTTPJudgeProvider"]
