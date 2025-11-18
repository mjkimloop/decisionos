"""
apps/judge/slo_judge.py

Evidence JSON과 SLO JSON을 비교해 pass/fail을 판정한다.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from apps.judge.slo_schema import SLOCanary, SLOJudgeInfra, SLOSpec

REQUIRED_BLOCKS = ["meta", "witness", "usage", "rating", "quota", "budget", "anomaly", "integrity"]


def _recalc_signature(core: Dict[str, Any]) -> str:
    payload = json.dumps(core, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _check_perf_min_samples(perf: Dict[str, Any], spec: SLOSpec, reasons: List[str]) -> bool:
    ok = True
    count = perf.get("count")
    if count is None:
        return ok
    if spec.latency.min_samples and count < spec.latency.min_samples:
        reasons.append("perf.samples_insufficient_latency")
        ok = False
    if spec.error.min_samples and count < spec.error.min_samples:
        reasons.append("perf.samples_insufficient_error")
        ok = False
    return ok


def evaluate(evidence: Dict[str, Any], slo: Dict[str, Any]) -> Tuple[str, List[str]]:
    reasons: List[str] = []
    try:
        spec = SLOSpec.model_validate(slo)
    except ValidationError as exc:
        return "fail", [f"slo-parse:{exc}"]

    for key in REQUIRED_BLOCKS:
        if key not in evidence:
            reasons.append(f"evidence.missing:{key}")
    if reasons:
        return "fail", reasons

    if spec.witness.require_csv_sha256 and not evidence["witness"].get("csv_sha256"):
        reasons.append("witness.no_csv_sha256")

    if spec.integrity.require_signature:
        core = {key: evidence[key] for key in REQUIRED_BLOCKS if key != "integrity"}
        for block in ("perf", "perf_judge", "judges", "canary"):
            if block in evidence and evidence[block] is not None:
                core[block] = evidence[block]
        expected = evidence["integrity"].get("signature_sha256")
        actual = _recalc_signature(core)
        if expected != actual:
            reasons.append("integrity.signature_mismatch")

    budget = evidence["budget"]
    if budget.get("level") not in spec.budget.allow_levels:
        reasons.append(f"budget.level_forbidden:{budget.get('level')}")
    if spec.budget.max_spent is not None and budget.get("spent", 0) > spec.budget.max_spent:
        reasons.append(f"budget.spent_over:{budget.get('spent')}>{spec.budget.max_spent}")

    quota = evidence["quota"].get("decisions", {})
    for metric, forbids in spec.quota.forbid_actions.items():
        action = quota.get(metric, {}).get("action")
        if action in forbids:
            reasons.append(f"quota.forbid:{metric}:{action}")

    if not spec.anomaly.allow_spike and evidence["anomaly"].get("is_spike", False):
        reasons.append("anomaly.spike_forbidden")

    perf_required = any(
        [
            spec.latency.max_p95_ms is not None,
            spec.latency.max_p99_ms is not None,
            spec.latency.min_samples is not None,
            spec.error.max_error_rate is not None,
            spec.error.min_samples is not None,
        ]
    )
    if perf_required:
        perf = evidence.get("perf")
        if not isinstance(perf, dict):
            reasons.append("perf.missing")
        else:
            if _check_perf_min_samples(perf, spec, reasons):
                latency_data = perf.get("latency_ms", {})
                if spec.latency.max_p95_ms is not None:
                    p95 = latency_data.get("p95", 0)
                    if p95 > spec.latency.max_p95_ms:
                        reasons.append(f"latency.p95_over:{p95}>{spec.latency.max_p95_ms}")
                if spec.latency.max_p99_ms is not None:
                    p99 = latency_data.get("p99", 0)
                    if p99 > spec.latency.max_p99_ms:
                        reasons.append(f"latency.p99_over:{p99}>{spec.latency.max_p99_ms}")
                if spec.error.max_error_rate is not None:
                    err_rate = perf.get("error_rate", 0)
                    if err_rate > spec.error.max_error_rate:
                        reasons.append(f"error.rate_over:{err_rate}>{spec.error.max_error_rate}")

    _evaluate_infra(spec.judge_infra, evidence, reasons)
    _evaluate_canary(spec.canary, evidence, reasons)
    _evaluate_drift(spec.drift, evidence, reasons)
    _check_saturation(evidence, spec, reasons)

    return ("pass" if not reasons else "fail"), reasons


def _evaluate_infra(spec: Optional[SLOJudgeInfra], evidence: Dict[str, Any], reasons: List[str]) -> None:
    if spec is None:
        return

    perf = evidence.get("perf_judge")
    if not isinstance(perf, dict):
        reasons.append("infra.perf_missing")
        return

    count = perf.get("count", 0)
    burst = 1.0 + (spec.grace_burst or 0.0)

    if spec.latency and spec.latency.min_samples and count < spec.latency.min_samples:
        reasons.append("infra.samples_insufficient_latency")
        return
    if spec.sig and spec.sig.min_samples and count < spec.sig.min_samples:
        reasons.append("infra.samples_insufficient_signature")
        return

    latency_data = perf.get("latency_ms", {})
    if spec.latency:
        if spec.latency.max_p95_ms is not None:
            allowed = spec.latency.max_p95_ms * burst
            p95 = latency_data.get("p95", 0)
            if p95 > allowed:
                reasons.append(f"infra.latency_p95_over:{p95}>{spec.latency.max_p95_ms}")
        if spec.latency.max_p99_ms is not None:
            allowed = spec.latency.max_p99_ms * burst
            p99 = latency_data.get("p99", 0)
            if p99 > allowed:
                reasons.append(f"infra.latency_p99_over:{p99}>{spec.latency.max_p99_ms}")

    if spec.availability and spec.availability.min_availability is not None:
        availability = perf.get("availability", 0)
        if availability < spec.availability.min_availability:
            reasons.append(f"infra.availability_low:{availability}<{spec.availability.min_availability}")

    if spec.sig and spec.sig.max_sig_error_rate is not None:
        sig_rate = perf.get("signature_error_rate", 0)
        if sig_rate > spec.sig.max_sig_error_rate:
            reasons.append(f"infra.sig_error_rate_over:{sig_rate}>{spec.sig.max_sig_error_rate}")


def _evaluate_canary(spec: Optional[SLOCanary], evidence: Dict[str, Any], reasons: List[str]) -> None:
    if spec is None:
        return
    block = evidence.get("canary")
    if block is None:
        reasons.append("canary.block_missing")
        return
    canary_perf = block.get("canary_perf") or {}
    deltas = block.get("deltas") or {}
    sample_count = canary_perf.get("count", 0)
    if sample_count < spec.min_sample_count:
        reasons.append("canary.sample_insufficient")

    thresholds = spec.thresholds
    if "p95_rel" in deltas and deltas["p95_rel"] > thresholds.max_p95_rel_increase:
        reasons.append(f"canary.p95_rel_over:{deltas['p95_rel']}>{thresholds.max_p95_rel_increase}")
    if "error_delta" in deltas and deltas["error_delta"] > thresholds.max_error_abs_delta:
        reasons.append(f"canary.error_delta_over:{deltas['error_delta']}>{thresholds.max_error_abs_delta}")
    if "sig_error_delta" in deltas and deltas["sig_error_delta"] > thresholds.max_sig_error_delta:
        reasons.append(f"canary.sig_error_delta_over:{deltas['sig_error_delta']}>{thresholds.max_sig_error_delta}")


def _evaluate_drift(spec: Optional[Any], evidence: Dict[str, Any], reasons: List[str]) -> None:
    """
    Drift SLO 검증
    posterior_drift.json 파일을 읽어서 severity, abs_diff, kl 검사
    """
    if spec is None:
        return

    import os
    from apps.judge.slo_schema import SLODrift

    # SLODrift 타입 검증
    if not isinstance(spec, SLODrift):
        return

    path = spec.source
    if not os.path.exists(path):
        reasons.append("drift.source_missing")
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        reasons.append("drift.source_unreadable")
        return

    sev = str(d.get("severity", "info"))
    abs_diff = float(d.get("abs_diff", 0.0))
    kl = float(d.get("kl", 0.0))

    # Severity 검사
    if sev in set(spec.forbid_severity):
        reasons.append(f"drift.severity_forbidden:{sev}")

    # abs_diff 검사
    if abs_diff > spec.max_abs_diff:
        reasons.append(f"drift.abs_over:{abs_diff}>{spec.max_abs_diff}")

    # KL divergence 검사
    if kl > spec.max_kl:
        reasons.append(f"drift.kl_over:{kl}>{spec.max_kl}")

def _check_saturation(evidence: Dict[str, Any], spec: SLOSpec, reasons: List[str]) -> bool:
    """Check resource saturation limits"""
    if not spec.saturation:
        return True
    
    ok = True
    usage = evidence.get("usage", {})
    
    # Check CPU saturation
    if spec.saturation.max_cpu_percent is not None:
        cpu_percent = usage.get("cpu_percent")
        if cpu_percent and cpu_percent > spec.saturation.max_cpu_percent:
            reasons.append(f"infra.saturation.cpu")
            ok = False
    
    # Check memory saturation
    if spec.saturation.max_mem_percent is not None:
        mem_percent = usage.get("mem_percent")
        if mem_percent and mem_percent > spec.saturation.max_mem_percent:
            reasons.append(f"infra.saturation.mem")
            ok = False
    
    # Check QPS saturation
    if spec.saturation.max_qps is not None:
        qps = usage.get("qps")
        if qps and qps > spec.saturation.max_qps:
            reasons.append(f"infra.saturation.qps")
            ok = False
    
    return ok
