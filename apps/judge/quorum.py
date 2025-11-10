"""
apps/judge/quorum.py

멀티-저지 쿼럼 판정 (k-of-n consensus)
"""
from __future__ import annotations
from typing import Callable, Dict, Any, List, Tuple

Verdict = Tuple[str, List[str]]  # ("pass"/"fail", reasons)
Provider = Callable[[Dict[str, Any], Dict[str, Any]], Verdict]


def decide(
    providers: List[Provider],
    evidence: Dict[str, Any],
    slo: Dict[str, Any],
    k: int,
    n: int,
) -> Dict[str, Any]:
    """
    멀티-저지 쿼럼 판정.

    Parameters:
        providers: Judge 함수 리스트 (각각 evaluate 시그니처)
        evidence: Evidence JSON
        slo: SLO JSON
        k: 필요한 최소 pass 수
        n: 전체 judge 수

    Returns:
        {
            "final": "pass" | "fail",
            "pass_count": int,
            "k": int,
            "n": int,
            "votes": [{"idx": int, "decision": str, "reasons": [str]}]
        }
    """
    assert 0 < k <= n == len(providers), f"Invalid quorum: k={k}, n={n}, providers={len(providers)}"

    votes: List[Dict[str, Any]] = []
    pass_cnt = 0

    for i, provider in enumerate(providers):
        dec, reasons = provider(evidence, slo)
        votes.append({"idx": i, "decision": dec, "reasons": reasons})
        if dec == "pass":
            pass_cnt += 1

    final = "pass" if pass_cnt >= k else "fail"

    return {"final": final, "pass_count": pass_cnt, "k": k, "n": n, "votes": votes}
