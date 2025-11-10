import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.gate_t]

from apps.obs.witness.judge_perf_io import JudgeRequest, parse_judge_log_csv, summarize_judge_perf


def test_parse_and_summarize_judge_perf(tmp_path: Path):
    csv_path = tmp_path / "perf.csv"
    csv_path.write_text(
        "\n".join(
            [
                "ts,status,latency_ms,signature_error",
                "2025-11-10T00:00:00Z,200,120,0",
                "2025-11-10T00:00:01Z,503,1800,0",
                "2025-11-10T00:00:02Z,200,80,1",
                "2025-11-10T00:00:03Z,429,200,0",
                "2025-11-10T00:00:04Z,200,60,0",
            ]
        ),
        encoding="utf-8",
    )

    rows = parse_judge_log_csv(csv_path)
    assert isinstance(rows[0], JudgeRequest)
    summary = summarize_judge_perf(rows)
    assert summary["count"] == 5
    assert summary["latency_ms"]["p95"] >= summary["latency_ms"]["p50"]
    assert pytest.approx(summary["availability"], rel=1e-3) == 0.8  # 1 - (1 / 5)
    assert pytest.approx(summary["error_rate"], rel=1e-3) == 0.4  # 503 + 429
    assert pytest.approx(summary["signature_error_rate"], rel=1e-3) == 0.2
