from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from apps.common.clock import drift_seconds, now_utc


def main() -> None:
    parser = argparse.ArgumentParser(description="Ensure local clock is within allowed drift")
    parser.add_argument("--ref", default="var/clock/reference_utc.txt")
    parser.add_argument("--max-skew-sec", type=float, default=5.0)
    args = parser.parse_args()

    ref_path = Path(args.ref)
    if not ref_path.exists():
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_path.write_text(now_utc().strftime("%Y-%m-%dT%H:%M:%SZ"), encoding="utf-8")
        print(f"[clock_guard] reference created at {ref_path}")
        return

    try:
        ref = datetime.fromisoformat(ref_path.read_text(encoding="utf-8").strip().replace("Z", "+00:00"))
    except Exception as exc:  # pragma: no cover - invalid file contents
        print(f"[clock_guard] invalid reference timestamp: {exc}", file=sys.stderr)
        sys.exit(2)

    delta = drift_seconds(now_utc(), ref)
    print(f"[clock_guard] drift={delta:.3f}s (limit={args.max_skew_sec}s)")
    if delta > args.max_skew_sec:
        print("[clock_guard] FAIL: drift too large", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
