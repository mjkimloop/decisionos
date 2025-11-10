"""
apps/judge/slo_judge.py

Evidence JSON과 SLO JSON을 비교하여 배포 판정(pass/fail) 수행.
"""
from __future__ import annotations
import json
import hashlib
from typing import Tuple, Dict, Any, List, Optional
from pydantic import ValidationError

from apps.judge.slo_schema import SLOCanary, SLOJudgeInfra, SLOSpec


def _recalc_signature(core: Dict[str, Any]) -> str:
    """핵심 필드로 무결성 서명 재계산"""
    payload = json.dumps(core, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def evaluate(
    evidence: Dict[str, Any], slo: Dict[str, Any]
) -> Tuple[str, List[str]]:
    """
    Evidence와 SLO를 비교하여 판정.

    Returns:
        ("pass" | "fail", reasons[])
    """
    reasons: List[str] = []

    # SLO 파싱
    try:
        spec = SLOSpec.model_validate(slo)
    except ValidationError as e:
        return "fail", [f"slo-parse:{e}"]

    # 필수 블록 검증
    required_keys = [
        "meta",
        "witness",
        "usage",
        "rating",
        "quota",
        "budget",
        "anomaly",
        "integrity",
    ]
    for key in required_keys:
        if key not in evidence:
            reasons.append(f"evidence.missing:{key}")
    if reasons:
        return "fail", reasons

    # witness / integrity 검증
    if spec.witness.require_csv_sha256 and not evidence["witness"].get("csv_sha256"):
        reasons.append("witness.no_csv_sha256")

    if spec.integrity.require_signature:
        core = {
            k: evidence[k]
            for k in [
                "meta",
                "witness",
                "usage",
                "rating",
                "quota",
                "budget",
                "anomaly",
            ]
        }
        for block in ("perf", "perf_judge", "judges", "canary"):
            if block in evidence and evidence[block] is not None:
                core[block] = evidence[block]
        expected_sig = evidence["integrity"].get("signature_sha256")
        actual_sig = _recalc_signature(core)
        if expected_sig != actual_sig:
            reasons.append("integrity.signature_mismatch")

    # budget 검증
    b = evidence["budget"]
    level = b.get("level")
    if level not in spec.budget.allow_levels:
        reasons.append(f"budget.level_forbidden:{level}")

    if spec.budget.max_spent is not None:
        spent = b.get("spent", 0)
        if spent > spec.budget.max_spent:
            reasons.append(f"budget.spent_over:{spent}>{spec.budget.max_spent}")

    # quota 검증
    q = evidence["quota"].get("decisions", {})
    for metric, forbids in spec.quota.forbid_actions.items():
        act = q.get(metric, {}).get("action")
        if act in forbids:
            reasons.append(f"quota.forbid:{metric}:{act}")

    # anomaly 검증
    if not spec.anomaly.allow_spike and evidence["anomaly"].get("is_spike", False):
        reasons.append("anomaly.spike_forbidden")

    # perf 검증 (latency/error 정책이 존재할 때)
    perf_required = (
        spec.latency.max_p95_ms is not None
        or spec.latency.max_p99_ms is not None
        or spec.error.max_error_rate is not None
    )
    if perf_required:
        if "perf" not in evidence or evidence["perf"] is None:
            reasons.append("perf.missing")
        else:
            perf = evidence["perf"]
            # latency 검증
            if spec.latency.max_p95_ms is not None:
                p95 = perf.get("latency_ms", {}).get("p95", 0)
                if p95 > spec.latency.max_p95_ms:
                    reasons.append(f"latency.p95_over:{p95}>{spec.latency.max_p95_ms}")

            if spec.latency.max_p99_ms is not None:
                p99 = perf.get("latency_ms", {}).get("p99", 0)
                if p99 > spec.latency.max_p99_ms:
                    reasons.append(f"latency.p99_over:{p99}>{spec.latency.max_p99_ms}")

            # error 검증
            if spec.error.max_error_rate is not None:
                err_rate = perf.get("error_rate", 0)
                if err_rate > spec.error.max_error_rate:
                    reasons.append(
                        f"error.rate_over:{err_rate}>{spec.error.max_error_rate}"
                    )

    _evaluate_infra(spec.judge_infra, evidence, reasons)
    _evaluate_canary(spec.canary, evidence, reasons)

    return ("pass" if not reasons else "fail"), reasons


def _evaluate_infra(spec: Optional[SLOJudgeInfra], evidence: Dict[str, Any], reasons: List[str]) -> None:
    if spec is None:
        return

    perf = evidence.get("perf_judge")
    if perf is None:
        reasons.append("infra.perf_missing")
        return

    latency_data = perf.get("latency_ms", {})
    if spec.latency:
        if spec.latency.max_p95_ms is not None:
            p95 = latency_data.get("p95", 0)
            if p95 > spec.latency.max_p95_ms:
                reasons.append(f"infra.latency_p95_over:{p95}>{spec.latency.max_p95_ms}")
        if spec.latency.max_p99_ms is not None:
            p99 = latency_data.get("p99", 0)
            if p99 > spec.latency.max_p99_ms:
                reasons.append(f"infra.latency_p99_over:{p99}>{spec.latency.max_p99_ms}")

    if spec.availability and spec.availability.min_availability is not None:
        availability = perf.get("availability", 0)
        if availability < spec.availability.min_availability:
            reasons.append(
                f"infra.availability_low:{availability}<{spec.availability.min_availability}"
            )

    if spec.sig and spec.sig.max_sig_error_rate is not None:
        sig_rate = perf.get("signature_error_rate", 0)
        if sig_rate > spec.sig.max_sig_error_rate:
            reasons.append(
                f"infra.sig_error_rate_over:{sig_rate}>{spec.sig.max_sig_error_rate}"
            )


def _evaluate_canary(spec: Optional[SLOCanary], evidence: Dict[str, Any], reasons: List[str]) -> None:
    if spec is None:
        return
    block = evidence.get("canary")
    if block is None:
        reasons.append("canary.block_missing")
        return
    canary_perf = block.get("canary_perf") or {}
    control_perf = block.get("control_perf") or {}
    deltas = block.get("deltas") or {}
    sample_count = canary_perf.get("count", 0)
    if sample_count < spec.min_sample_count:
        reasons.append("canary.sample_insufficient")
    thresholds = spec.thresholds
    if "p95_rel" in deltas and deltas["p95_rel"] > thresholds.max_p95_rel_increase:
        reasons.append(
            f"canary.p95_rel_over:{deltas['p95_rel']}>{thresholds.max_p95_rel_increase}"
        )
    if "error_delta" in deltas and deltas["error_delta"] > thresholds.max_error_abs_delta:
        reasons.append(
            f"canary.error_delta_over:{deltas['error_delta']}>{thresholds.max_error_abs_delta}"
        )
    if (
        "sig_error_delta" in deltas
        and deltas["sig_error_delta"] > thresholds.max_sig_error_delta
    ):
        reasons.append(
            f"canary.sig_error_delta_over:{deltas['sig_error_delta']}>{thresholds.max_sig_error_delta}"
        )
