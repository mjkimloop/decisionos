from __future__ import annotations

import argparse
import json
from pathlib import Path

from apps.obs.witness.judge_perf_io import parse_judge_log_csv, summarize_judge_perf


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="dosctl witness judge-perf")
    parser.add_argument("--csv", required=True, help="judge request log CSV path")
    parser.add_argument("--out", required=True, help="output JSON path")
    args = parser.parse_args(argv)

    requests = parse_judge_log_csv(args.csv)
    summary = summarize_judge_perf(requests)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[dosctl] judge perf summary -> {out_path}")


if __name__ == "__main__":
    main()
