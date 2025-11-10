from __future__ import annotations

import json
from pathlib import Path

import pytest

from cli.dosctl.exp_judge import (
    Comparison,
    parse_expression,
    evaluate_expression,
    run_cli_judge,
)


def test_parse_expression_basic():
    comps = parse_expression("latency_p95 <= 1200 AND err_rate < 0.01")
    assert comps == [
        Comparison("latency_p95", "<=", 1200.0),
        Comparison("err_rate", "<", 0.01),
    ]


def test_parse_expression_invalid_clause():
    with pytest.raises(ValueError):
        parse_expression("latency_p95 <> 100")


def test_evaluate_expression_pass_and_fail():
    comparisons = parse_expression("latency_p95 <= 100 AND err_rate <= 0.1")
    verdict, failures = evaluate_expression(comparisons, {"latency_p95": 50, "err_rate": 0.05})
    assert verdict is True and not failures

    verdict, failures = evaluate_expression(comparisons, {"latency_p95": 150, "err_rate": 0.05})
    assert verdict is False
    assert any("latency_p95" in failure for failure in failures)


def test_evaluate_expression_missing_metric():
    comparisons = parse_expression("latency_p95 <= 100")
    verdict, failures = evaluate_expression(comparisons, {})
    assert verdict is False
    assert failures == ["latency_p95 missing"]


def test_run_cli_judge_writes_output(tmp_path: Path):
    witness = {
        "latency_p95": 800,
        "err_rate": 0.005,
        "citation_cov": 0.99,
        "parity_delta": 0.002,
        "cost_krw": 10,
    }
    slo = {
        "routes": [
            {
                "route_id": "RAG_Answer_Standard",
                "slo": {"p95_ms": 1200, "err_rate": 0.01, "ai_citation_cov": 0.98},
            },
            {
                "route_id": "Eligibility_Path_A",
                "slo": {"p95_ms": 900, "err_rate": 0.005, "ag_mapping_loss": 0.005},
            },
        ]
    }
    witness_path = tmp_path / "witness.json"
    slo_path = tmp_path / "slo.json"
    output_path = tmp_path / "verdicts_cli.json"
    witness_path.write_text(json.dumps(witness), encoding="utf-8")
    slo_path.write_text(json.dumps(slo), encoding="utf-8")

    payload = run_cli_judge(witness_path, slo_path, output_path)
    assert output_path.exists()
    assert payload["overall_verdict"] == "PASS"
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert set(data["routes"].keys()) == {"RAG_Answer_Standard", "Eligibility_Path_A"}
