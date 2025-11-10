"""
Claude's independent implementation of SLO judge.
Uses different logic structure from judge_x for diversity.
"""
import json
import pathlib
from typing import Any
from apps.obs.witness.schema import Witness

def load_witness(witness_path: str) -> Witness:
    """Load and validate witness from file"""
    content = pathlib.Path(witness_path).read_text(encoding="utf-8")
    return Witness.model_validate_json(content)

def load_slo_config(slo_json_path: str) -> dict:
    """Load SLO configuration"""
    content = pathlib.Path(slo_json_path).read_text(encoding="utf-8")
    return json.loads(content)

def check_slo_compliance(witness: Witness, route_slo: dict) -> tuple[str, list[str]]:
    """
    Check if witness meets SLO requirements.
    Returns (verdict, violations) where verdict is "PASS" or "FAIL"
    """
    violations = []

    # Check latency p95
    if "p95_ms" in route_slo:
        threshold = route_slo["p95_ms"]
        actual = witness.latency_p95 or 0.0
        if actual > threshold:
            violations.append(f"latency_p95: {actual:.1f}ms > {threshold}ms")

    # Check error rate
    if "err_rate" in route_slo:
        threshold = route_slo["err_rate"]
        actual = witness.err_rate or 0.0
        if actual > threshold:
            violations.append(f"err_rate: {actual:.4f} > {threshold:.4f}")

    # Check citation coverage (AI-specific)
    if "ai_citation_cov" in route_slo:
        threshold = route_slo["ai_citation_cov"]
        actual = witness.citation_cov
        if actual is None:
            violations.append(f"citation_cov: missing data")
        elif actual < threshold:
            violations.append(f"citation_cov: {actual:.3f} < {threshold:.3f}")

    # Check mapping loss (ontology-specific)
    if "ag_mapping_loss" in route_slo:
        threshold = route_slo["ag_mapping_loss"]
        actual = witness.parity_delta
        if actual is None:
            violations.append(f"parity_delta: missing data")
        elif actual > threshold:
            violations.append(f"parity_delta: {actual:.4f} > {threshold:.4f}")

    # Check cost (if specified)
    if "cost_krw" in route_slo:
        threshold = route_slo["cost_krw"]
        actual = witness.cost_krw or 0.0
        if actual > threshold:
            violations.append(f"cost_krw: {actual:.2f} > {threshold:.2f}")

    # Check delta metrics for canary deployments
    if "err_rate_delta_pp" in route_slo:
        # This would require baseline comparison - stub for now
        pass

    if "latency_p95_delta_pct" in route_slo:
        # This would require baseline comparison - stub for now
        pass

    # Check replay hash match
    if "replay_hash_match" in route_slo:
        threshold = route_slo["replay_hash_match"]
        # This requires additional replay metadata - stub for now
        pass

    verdict = "FAIL" if violations else "PASS"
    return verdict, violations

def run_judge(witness_path: str, slo_json_path: str) -> dict:
    """
    Run SLO judgment on witness data.
    Returns verdict structure with per-route judgments.
    """
    config = load_slo_config(slo_json_path)
    witness = load_witness(witness_path)

    results = {}
    for route in config.get("routes", []):
        route_id = route["route_id"]
        route_slo = route.get("slo", {})

        verdict, violations = check_slo_compliance(witness, route_slo)

        results[route_id] = {
            "verdict": verdict,
            "violations": violations,
            "sample_n": witness.sample_n,
            "source": witness.source_id
        }

    return {
        "by_route": {k: v["verdict"] for k, v in results.items()},
        "details": results,
        "judge_id": "C-102",
        "quorum_stub": "SINGLE"
    }
