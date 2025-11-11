from __future__ import annotations

import asyncio
import secrets
import time
from typing import Any, Callable, Dict, Optional

import httpx

from .base import JudgeProvider
from apps.judge.crypto import MultiKeyLoader, hmac_sign
from apps.judge.errors import JudgeBadSignature, JudgeHTTPError, JudgeTimeout
from apps.judge.backpressure import (
    TokenBucket, CircuitBreaker, calculate_backoff_ms,
    RATE_LIMIT_PER_SECOND, RATE_LIMIT_BURST,
    CIRCUIT_BREAKER_THRESHOLD, CIRCUIT_BREAKER_TIMEOUT_SEC
)


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
        breaker_max_failures: int = CIRCUIT_BREAKER_THRESHOLD,
        breaker_reset_seconds: float = CIRCUIT_BREAKER_TIMEOUT_SEC,
        verify_ssl: bool = True,
        client_factory: Optional[Callable[[], httpx.AsyncClient]] = None,
        enable_rate_limit: bool = True,
    ) -> None:
        super().__init__(provider_id)
        self.url = url
        self.timeout = timeout_ms / 1000
        self.retries = retries
        self.require_signature = require_signature
        self.key_id = key_id or "k1"
        self._verify_ssl = verify_ssl
        self._client_factory = client_factory or (
            lambda: httpx.AsyncClient(timeout=self.timeout, verify=self._verify_ssl)
        )
        self._key_loader = MultiKeyLoader()

        # 표준 백프레셔 정책
        self._rate_limiter = TokenBucket(
            capacity=RATE_LIMIT_BURST,
            refill_rate=RATE_LIMIT_PER_SECOND
        ) if enable_rate_limit else None

        self._circuit_breaker = CircuitBreaker(
            threshold=breaker_max_failures,
            timeout_sec=int(breaker_reset_seconds),
            half_open_requests=3
        )

    def _record_failure(self) -> None:
        """실패 기록 - 서킷 브레이커에 전파"""
        try:
            def fail_func():
                raise Exception("Judge evaluation failed")
            self._circuit_breaker.call(fail_func)
        except Exception:
            pass  # 서킷 브레이커에 실패 기록됨

    def get_backpressure_stats(self) -> Dict[str, Any]:
        """백프레셔 상태 반환"""
        stats = {
            "circuit_breaker": self._circuit_breaker.get_stats(),
        }
        if self._rate_limiter:
            stats["rate_limiter"] = self._rate_limiter.get_stats()
        return stats

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
        # 레이트 리밋 체크
        if self._rate_limiter and not self._rate_limiter.consume():
            raise JudgeHTTPError(429, f"rate limit exceeded for provider {self.provider_id}")

        # 서킷 브레이커 체크
        breaker_stats = self._circuit_breaker.get_stats()
        if breaker_stats["state"] == "open":
            raise JudgeHTTPError(503, f"circuit breaker OPEN for provider {self.provider_id}")

        attempt = 0
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

                    # 성공 시 서킷 브레이커 리셋
                    def success_func():
                        return vote
                    self._circuit_breaker.call(success_func)
                    return vote

            except httpx.TimeoutException as exc:
                last_exc = JudgeTimeout(str(exc))
                self._record_failure()
            except JudgeBadSignature as exc:
                last_exc = exc
                self._record_failure()
                break
            except JudgeHTTPError as exc:
                last_exc = exc
                if exc.status_code >= 500:
                    self._record_failure()
                else:
                    break
            except httpx.RequestError as exc:
                last_exc = exc
                self._record_failure()
            finally:
                if attempt <= self.retries:
                    # 지수 백오프
                    backoff_ms = calculate_backoff_ms(attempt - 1)
                    await asyncio.sleep(backoff_ms / 1000)

        assert last_exc is not None
        raise last_exc


__all__ = ["HTTPJudgeProvider"]
