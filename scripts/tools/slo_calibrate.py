from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


DEFAULTS = {
    "latency": {"max_p95_ms": 900, "max_p99_ms": 1800, "min_samples": 1000},
    "error": {"max_error_rate": 0.01, "min_samples": 500},
}


def calibrate(lookback: str, out: str) -> Dict[str, Any]:
    # Placeholder: in real use, load metrics for the lookback window and compute percentiles.
    payload = {"lookback": lookback, "calibrated_at": Path(out).as_posix(), **DEFAULTS}
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="SLO calibration stub")
    ap.add_argument("--lookback", default="72h")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    payload = calibrate(args.lookback, args.out)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
