from __future__ import annotations

import argparse
import json
from pathlib import Path

from apps.obs.evidence.indexer import scan_evidence_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan evidence directory and produce index.json")
    parser.add_argument("--root", default="var/evidence")
    parser.add_argument("--out", default="var/evidence/index.json")
    args = parser.parse_args()

    index = scan_evidence_dir(args.root)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[indexer] wrote {out_path} (count={index['count']})")


if __name__ == "__main__":
    main()
