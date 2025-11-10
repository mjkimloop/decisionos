from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict

import sys
import importlib.util

ROOTS = [
    Path(__file__).resolve().parents[3],
    Path(__file__).resolve().parents[4],
]
for root in ROOTS:
    if root.exists() and str(root) not in sys.path:
        sys.path.insert(0, str(root))

try:
    from apps.obs.witness.exporter_x import export_witness
except ModuleNotFoundError:
    for root in ROOTS:
        module_path = root / "apps" / "obs" / "witness" / "exporter_x.py"
        if module_path.exists():
            spec = importlib.util.spec_from_file_location("apps.obs.witness.exporter_x", module_path)
            module = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            module.__package__ = "apps.obs.witness"
            spec.loader.exec_module(module)
            export_witness = module.export_witness
            break
    else:
        raise


def _generate_events(n: int, target_p95: float, err_rate: float) -> List[Dict[str, float]]:
    rng = random.Random(42)
    events: List[Dict[str, float]] = []
    err_rate = max(0.0, min(err_rate, 1.0))
    for i in range(n):
        quantile = (i + 1) / (n + 1)
        if quantile < 0.95:
            latency = quantile * target_p95 * rng.uniform(0.85, 0.98)
        else:
            latency = target_p95 * rng.uniform(0.95, 1.2)
        events.append(
            {
                "latency_ms": float(latency),
                "err": 1 if rng.random() < err_rate else 0,
                "cost_krw": round(rng.uniform(0.05, 0.5), 4),
                "cite_ok": 1 if rng.random() > 0.02 else 0,
                "parity_delta": rng.uniform(0.0, 0.01),
            }
        )
    return events


def _write_jsonl(path: Path, events: List[Dict[str, float]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")


def generate_golden_trace(
    output_dir: Path,
    target_p95: float,
    err_rate: float,
    sample_n: int,
    build_id: str,
    commit_sha: str,
) -> Dict[str, str]:
    events = _generate_events(sample_n, target_p95, err_rate)
    period_end = datetime.now(timezone.utc)
    period_start = period_end - timedelta(hours=24)
    witness = export_witness(
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        events=events,
        build_id=build_id,
        commit_sha=commit_sha,
        source_id="golden_trace",
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "raw_events.jsonl"
    witness_path = output_dir / "witness.json"
    _write_jsonl(raw_path, events)
    witness_path.write_text(witness.model_dump_json(indent=2), encoding="utf-8")

    return {"raw": str(raw_path), "witness": str(witness_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate golden trace witness + raw events")
    parser.add_argument("--p95", type=float, required=True, help="Target latency p95 in ms")
    parser.add_argument("--err", type=float, required=True, help="Target error rate (0-1)")
    parser.add_argument("--n", type=int, default=1000, help="Sample size")
    parser.add_argument("--output", type=Path, default=Path("evidence/golden"), help="Output directory")
    parser.add_argument("--build-id", default="golden-build", help="Build identifier to embed in witness")
    parser.add_argument("--commit-sha", default="golden-sha", help="Commit SHA to embed in witness")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = generate_golden_trace(args.output, args.p95, args.err, args.n, args.build_id, args.commit_sha)
    print(json.dumps(paths, indent=2))


if __name__ == "__main__":
    main()
