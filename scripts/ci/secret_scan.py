from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

PATTERNS = {
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "slack_token": re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}"),
    "generic_secret": re.compile(r"(?i)(secret|token|apikey)[\"' ]*[:=][\"' ]*[A-Za-z0-9/\-_]{16,}"),
}


def iter_files(paths: List[str]) -> List[Path]:
    files: List[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            for candidate in path.rglob("*"):
                if candidate.is_file():
                    files.append(candidate)
    return files


IGNORE_TOKEN = "secret-scan: ignore"


def scan_file(path: Path) -> List[Tuple[str, str]]:
    hits: List[Tuple[str, str]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return hits
    for idx, line in enumerate(lines, start=1):
        if IGNORE_TOKEN in line:
            continue
        for name, pattern in PATTERNS.items():
            for match in pattern.finditer(line):
                snippet = match.group(0)
                hits.append((name, snippet))
    return hits


def main() -> None:
    parser = argparse.ArgumentParser(description="Secret scanner")
    parser.add_argument("--paths", nargs="+", default=["."], help="Files or directories to scan")
    parser.add_argument("--fail-on-hit", type=int, default=0, help="Exit with 1 when hits are found")
    args = parser.parse_args()

    all_hits: Dict[str, List[Tuple[str, str]]] = {}
    for path in iter_files(args.paths):
        hits = scan_file(path)
        if hits:
            all_hits[str(path)] = hits

    if not all_hits:
        print("[secret_scan] no hits")
        return

    for path, hits in all_hits.items():
        print(f"[secret_scan] {path}")
        for pattern, snippet in hits:
            print(f"  - {pattern}: {snippet[:40]}")

    if args.fail_on_hit:
        sys.exit(1)


if __name__ == "__main__":
    main()
