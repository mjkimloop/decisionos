from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
import importlib.util
from typing import Dict, List, Tuple

ROOTS = [
    Path(__file__).resolve().parents[3],
    Path(__file__).resolve().parents[4],
]
for root in ROOTS:
    if root.exists() and str(root) not in sys.path:
        sys.path.insert(0, str(root))


def _load_from_roots(module_rel_path: Path, dotted: str):
    for root in ROOTS:
        module_path = root / module_rel_path
        if module_path.exists():
            spec = importlib.util.spec_from_file_location(dotted, module_path)
            module = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            module.__package__ = dotted.rsplit(".", 1)[0]
            spec.loader.exec_module(module)
            return module
    raise ModuleNotFoundError(dotted)


try:
    from apps.obs.witness.exporter_x import export_witness
except ModuleNotFoundError:
    module = _load_from_roots(Path("apps/obs/witness/exporter_x.py"), "apps.obs.witness.exporter_x")
    export_witness = module.export_witness

try:
    from cli.dosctl.exp_judge import load_json
except ModuleNotFoundError:
    module = _load_from_roots(Path("cli/dosctl/exp_judge.py"), "cli.dosctl.exp_judge")
    load_json = module.load_json

METRIC_TOLERANCES = {
    "latency_p95": ("latency_p95_delta_pct", "percent"),
    "err_rate": ("err_rate_delta_pp", "absolute"),
    "cost_krw": ("cost_krw_delta_pct", "percent"),
    "citation_cov": ("citation_cov_delta_pp", "absolute"),
    "parity_delta": ("parity_delta_pp", "absolute"),
}


def _compute_allowed(metric: str, base: float, tolerances: Dict[str, float]) -> float:
    tol_key, mode = METRIC_TOLERANCES[metric]
    tolerance_value = tolerances.get(tol_key, 0.0)
    if mode == "percent":
        if base == 0:
            return tolerance_value / 100.0 if tolerance_value else 0.0
        return abs(base) * (tolerance_value / 100.0)
    return tolerance_value


def reconcile_metrics(
    primary: Dict[str, float],
    candidate: Dict[str, float],
    tolerances: Dict[str, float],
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for metric in METRIC_TOLERANCES:
        primary_value = primary.get(metric)
        candidate_value = candidate.get(metric)
        if primary_value is None or candidate_value is None:
            rows.append(
                {
                    "metric": metric,
                    "primary": primary_value,
                    "candidate": candidate_value,
                    "delta": None,
                    "allowed_delta": None,
                    "status": "MISSING",
                }
            )
            continue
        delta = abs(float(candidate_value) - float(primary_value))
        allowed = _compute_allowed(metric, float(primary_value), tolerances)
        status = "PASS" if delta <= allowed else "FAIL"
        rows.append(
            {
                "metric": metric,
                "primary": float(primary_value),
                "candidate": float(candidate_value),
                "delta": delta,
                "allowed_delta": allowed,
                "status": status,
            }
        )
    return rows


def _read_raw_events(path: str | Path) -> List[Dict[str, float]]:
    events: List[Dict[str, float]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def _aggregate_candidate(
    events: List[Dict[str, float]],
    base_witness: Dict[str, object],
) -> Dict[str, object]:
    witness_obj = export_witness(
        period_start=str(base_witness.get("period_start")),
        period_end=str(base_witness.get("period_end")),
        events=events,
        build_id=str(base_witness.get("build_id", "backfill")),
        commit_sha=str(base_witness.get("commit_sha", "backfill")),
        source_id="backfill_runner",
    )
    return witness_obj.model_dump()


def run_backfill_reconcile(
    primary_witness_path: str | Path,
    raw_events_path: str | Path,
    slo_path: str | Path,
    output_dir: str | Path,
) -> Dict[str, object]:
    primary = load_json(primary_witness_path)
    events = _read_raw_events(raw_events_path)
    candidate = _aggregate_candidate(events, primary)
    tolerances = load_json(slo_path).get("measurement_quorum_tolerances", {})

    rows = reconcile_metrics(primary, candidate, tolerances)
    status = "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL"

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "backfill_report.json"
    csv_path = output_dir / "discrepancies.csv"

    payload = {
        "status": status,
        "witness_primary": str(primary_witness_path),
        "raw_events": str(raw_events_path),
        "metrics": rows,
    }
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=["metric", "primary", "candidate", "delta", "allowed_delta", "status"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reconcile witness vs. raw events backfill")
    parser.add_argument("--witness", required=True, help="Primary witness JSON path")
    parser.add_argument("--raw", required=True, help="Raw events JSONL path")
    parser.add_argument("--slo", default="configs/slo/slo.json", help="slo.json path")
    parser.add_argument("--output-dir", default=None, help="Output directory (defaults to witness dir)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir or Path(args.witness).resolve().parent
    run_backfill_reconcile(args.witness, args.raw, args.slo, output_dir)


if __name__ == "__main__":
    main()
