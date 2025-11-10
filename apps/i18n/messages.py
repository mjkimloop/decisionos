from __future__ import annotations

from typing import Dict


_MESSAGES: Dict[str, Dict[str, str]] = {
    "perf.p95_over": {
        "en-US": "P95 latency exceeds limit",
        "ko-KR": "p95 지연 한계를 초과했습니다",
    },
    "perf.p99_over": {
        "en-US": "P99 latency exceeds limit",
        "ko-KR": "p99 지연 한계를 초과했습니다",
    },
    "error.rate_over": {
        "en-US": "Error rate exceeds limit",
        "ko-KR": "에러율이 허용치를 초과했습니다",
    },
    "infra.samples_insufficient": {
        "en-US": "Insufficient infra samples",
        "ko-KR": "인프라 샘플 수가 부족합니다",
    },
    "infra.samples_insufficient_for_latency": {
        "en-US": "Infra latency samples insufficient",
        "ko-KR": "인프라 지연 샘플이 부족합니다",
    },
    "infra.samples_insufficient_for_error": {
        "en-US": "Infra error samples insufficient",
        "ko-KR": "인프라 오류 샘플이 부족합니다",
    },
    "quota.forbidden_action": {
        "en-US": "Quota forbids action",
        "ko-KR": "쿼터 정책상 허용되지 않은 동작입니다",
    },
    "budget.exceeded": {
        "en-US": "Budget exceeded",
        "ko-KR": "예산을 초과했습니다",
    },
    "integrity.signature_mismatch": {
        "en-US": "Integrity signature mismatch",
        "ko-KR": "무결성 서명이 일치하지 않습니다",
    },
    "canary.delta_exceeds": {
        "en-US": "Canary delta exceeds allowed threshold",
        "ko-KR": "카나리 편차가 허용치를 초과했습니다",
    },
    "infra.latency_p95_over": {
        "en-US": "Infra p95 latency exceeds limit",
        "ko-KR": "인프라 p95 지연이 한계를 초과했습니다",
    },
    "infra.latency_p99_over": {
        "en-US": "Infra p99 latency exceeds limit",
        "ko-KR": "인프라 p99 지연이 한계를 초과했습니다",
    },
    "infra.availability_breach": {
        "en-US": "Infra availability below target",
        "ko-KR": "인프라 가용성이 목표 이하입니다",
    },
}


def reason_message(code: str, locale: str = "en-US") -> str:
    """
    Return a localized, human-friendly message for a reason code.
    """
    entry = _MESSAGES.get(code)
    if not entry:
        return code
    return entry.get(locale) or entry.get("en-US") or next(iter(entry.values()))
