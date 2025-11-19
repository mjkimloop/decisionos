from __future__ import annotations

import json
import os
import time
import logging
from typing import Any, Dict

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover
    httpx = None

from apps.switchboard.adapters import local

log = logging.getLogger("switchboard.openai")


class OpenAIAdapter:
    def __init__(self):
        self.api_key = os.getenv("DECISIONOS_SB_OPENAI_API_KEY", "")
        self.timeout_ms = int(os.getenv("DECISIONOS_SB_OPENAI_TIMEOUT_MS", "8000"))
        self.max_cost_usd = float(os.getenv("DECISIONOS_SB_OPENAI_MAX_COST_USD", "0.50"))
        self.retry = int(os.getenv("DECISIONOS_SB_OPENAI_RETRY", "2"))
        self.fallback_mode = os.getenv("DECISIONOS_SB_OPENAI_FALLBACK", "local")

    def _fallback(self, prompt: str):
        return local.generate_local(prompt)

    def _estimate_cost(self, prompt: str) -> float:
        # 단순 근사: 토큰 길이 기반 비용 추정
        tokens = max(1, len(prompt) // 4)
        return tokens * 0.00002  # 약 $0.00002/token 가정

    def generate(self, prompt: str) -> Dict[str, Any]:
        if not httpx or not self.api_key:
            return {**self._fallback(prompt), "fallback_used": True, "reason": "missing_httpx_or_apikey"}

        estimated_cost = self._estimate_cost(prompt)
        if estimated_cost > self.max_cost_usd:
            return {**self._fallback(prompt), "fallback_used": True, "reason": "cost_exceeded"}

        last_exc = None
        for attempt in range(self.retry + 1):
            try:
                start = time.time()
                with httpx.Client(timeout=self.timeout_ms / 1000.0) as client:
                    resp = client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={
                            "model": "gpt-3.5-turbo",
                            "messages": [{"role": "user", "content": prompt}],
                        },
                    )
                latency = (time.time() - start) * 1000
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return {
                        "provider": "openai",
                        "prompt": prompt,
                        "generated": content,
                        "latency_ms": latency,
                        "fallback_used": False,
                    }
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < self.retry:
                    continue
                # 기타 오류는 폴백
                return {**self._fallback(prompt), "fallback_used": True, "reason": f"http_{resp.status_code}"}
            except Exception as exc:  # pragma: no cover
                last_exc = exc
                if attempt < self.retry:
                    continue
        log.warning("OpenAI fallback due to error: %s", last_exc)
        return {**self._fallback(prompt), "fallback_used": True, "reason": "exception"}


adapter = OpenAIAdapter()


def generate(prompt: str) -> Dict[str, Any]:
    return adapter.generate(prompt)
