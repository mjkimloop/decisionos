from __future__ import annotations

import argparse

from apps.obs.evidence.indexer import write_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build evidence index.json")
    parser.add_argument("--root", default="var/evidence")
    parser.add_argument("--out")
    args = parser.parse_args()
    out_path = write_index(args.root, args.out)
    print(f"[indexer] wrote {out_path}")


if __name__ == "__main__":
    main()
