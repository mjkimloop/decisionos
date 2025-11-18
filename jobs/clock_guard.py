from __future__ import annotations

import argparse
import sys
from pathlib import Path

from apps.common.clock_guard import check_clock, ensure_reference


def main() -> None:
    parser = argparse.ArgumentParser(description="Ensure local clock is within allowed drift")
    parser.add_argument("--ref", default="var/clock/reference_utc.txt")
    parser.add_argument("--max-skew-sec", type=float, default=5.0)
    args = parser.parse_args()

    ref_path = Path(args.ref)
    if not ref_path.exists():
        ensure_reference(args.ref)
        print(f"[clock_guard] reference created at {ref_path}")
        return

    try:
        ok, drift = check_clock(args.ref, args.max_skew_sec)
    except ValueError as exc:
        print(f"[clock_guard] {exc}", file=sys.stderr)
        sys.exit(2)

    print(f"[clock_guard] drift={drift:.3f}s (limit={args.max_skew_sec}s)")
    if not ok:
        print("[clock_guard] FAIL: drift too large", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
