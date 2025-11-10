from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Iterable, List

from .errors import JudgeError
from .providers.base import JudgeProvider


async def quorum_decide(
    providers: Iterable[JudgeProvider],
    evidence: Dict[str, Any],
    slo: Dict[str, Any],
    k: int,
    n: int,
    fail_closed_on_degrade: bool = True,
) -> Dict[str, Any]:
    providers = list(providers)
    if len(providers) != n:
        raise ValueError(f"provider count {len(providers)} != quorum n {n}")
    if not (0 < k <= n):
        raise ValueError(f"invalid quorum k={k}, n={n}")

    votes: List[Dict[str, Any]] = []
    pass_count = 0
    degraded = False

    async def _eval(provider: JudgeProvider) -> Dict[str, Any]:
        start = time.perf_counter()
        result = await provider.evaluate(evidence, slo)
        vote = {
            "id": result.get("id", provider.provider_id),
            "decision": result.get("decision"),
            "reasons": result.get("reasons", []),
            "meta": result.get("meta", {}),
            "version": result.get("version"),
        }
        vote["meta"].setdefault("latency_ms", round((time.perf_counter() - start) * 1000, 2))
        return vote

    tasks = [asyncio.create_task(_eval(p)) for p in providers]
    for task, provider in zip(tasks, providers):
        try:
            vote = await task
            votes.append(vote)
            if vote.get("decision") == "pass":
                pass_count += 1
        except JudgeError as exc:
            degraded = True
            votes.append(
                {
                    "id": provider.provider_id,
                    "decision": "fail",
                    "reasons": [str(exc)],
                    "meta": {"error": exc.__class__.__name__},
                }
            )
        except Exception as exc:  # pragma: no cover
            degraded = True
            votes.append(
                {
                    "id": provider.provider_id,
                    "decision": "fail",
                    "reasons": [str(exc)],
                    "meta": {"error": exc.__class__.__name__},
                }
            )

    final = "pass" if pass_count >= k else "fail"
    if degraded and fail_closed_on_degrade:
        final = "fail"

    return {
        "final": final,
        "k": k,
        "n": n,
        "pass_count": pass_count,
        "votes": votes,
        "degraded": degraded,
    }


__all__ = ["quorum_decide"]
