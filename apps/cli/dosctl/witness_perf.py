"""
apps/cli/dosctl/witness_perf.py

CLI: dosctl witness perf --csv <file> --out <file>
"""
import json
import sys
from pathlib import Path
from apps.obs.witness.perf import parse_reqlog_csv, summarize_perf


def main():
    import argparse

    ap = argparse.ArgumentParser(
        prog="dosctl witness perf",
        description="Parse reqlog CSV and generate performance summary",
    )
    ap.add_argument("--csv", required=True, help="Path to reqlog CSV file")
    ap.add_argument(
        "--out", required=True, help="Path to output JSON file (e.g., var/evidence/perf-latest.json)"
    )
    args = ap.parse_args()

    # CSV 파싱
    try:
        with open(args.csv, "r", encoding="utf-8") as f:
            reqs = parse_reqlog_csv(f)
    except Exception as e:
        print(f"[ERROR] Failed to parse CSV: {e}", file=sys.stderr)
        sys.exit(1)

    # 성능 요약 산출
    summary = summarize_perf(reqs)

    # JSON 출력
    try:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2, sort_keys=True)
        print(f"[OK] Performance summary written to: {out_path}")
    except Exception as e:
        print(f"[ERROR] Failed to write output: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
