from __future__ import annotations

import json
import pathlib
from typing import Dict

from apps.obs.witness.schema import Witness
from .quorum import quorum_verdict


def load_witness(path: str) -> Witness:
    data = pathlib.Path(path).read_text(encoding="utf-8")
    return Witness.model_validate_json(data)


def judge_route(witness: Witness, slo: Dict, tolerances: Dict) -> str:
    if "p95_ms" in slo and (witness.latency_p95 or 0.0) > slo["p95_ms"]:
        return "FAIL"
    if "err_rate" in slo and (witness.err_rate or 0.0) > slo["err_rate"]:
        return "FAIL"
    if "ai_citation_cov" in slo and (witness.citation_cov or 1.0) < slo["ai_citation_cov"]:
        return "FAIL"
    if "ag_mapping_loss" in slo and (witness.parity_delta or 0.0) > slo["ag_mapping_loss"]:
        return "FAIL"
    if "cost_krw" in slo and (witness.cost_krw or 0.0) > slo["cost_krw"]:
        return "FAIL"
    return "PASS"


def run_judge(witness_path: str, slo_json_path: str) -> Dict:
    slo_config = json.loads(pathlib.Path(slo_json_path).read_text(encoding="utf-8"))
    witness = load_witness(witness_path)

    verdicts = {}
    for route in slo_config.get("routes", []):
        verdicts[route["route_id"]] = judge_route(
            witness,
            route.get("slo", {}),
            slo_config.get("measurement_quorum_tolerances", {}),
        )

    quorum = quorum_verdict(verdicts.values(), require=2)
    return {"by_route": verdicts, "quorum_verdict": quorum}


__all__ = ["run_judge", "judge_route", "load_witness"]
