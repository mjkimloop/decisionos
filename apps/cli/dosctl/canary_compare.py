from __future__ import annotations

import argparse
import json
from pathlib import Path

from apps.obs.witness.canary_compare import compare


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="dosctl canary compare")
    parser.add_argument("--control", required=True, help="control CSV path")
    parser.add_argument("--canary", required=True, help="canary CSV path")
    parser.add_argument("--out", required=True, help="output JSON path")
    args = parser.parse_args(argv)

    result = compare(args.control, args.canary)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[dosctl] canary compare summary -> {out_path}")


if __name__ == "__main__":
    main()
