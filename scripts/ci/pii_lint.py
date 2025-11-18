from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "kr_phone": re.compile(r"(?:\+82-?|0)(?:10|1[1-9])[- ]?\d{3,4}[- ]?\d{4}"),
    "rrn": re.compile(r"\b\d{6}-?\d{7}\b"),
}


def iter_files(paths: List[str], exclude: List[str]) -> List[Path]:
    files: List[Path] = []
    excluded = {str(Path(e).resolve()) for e in exclude}
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            continue
        if path.is_file():
            files.append(path)
            continue
        for candidate in path.rglob("*"):
            if candidate.is_file():
                resolved = str(candidate.parent.resolve())
                if any(resolved.startswith(ex) for ex in excluded):
                    continue
                files.append(candidate)
    return files


def scan(path: Path) -> List[Tuple[str, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    hits: List[Tuple[str, str]] = []
    for name, regex in PATTERNS.items():
        for match in regex.finditer(text):
            hits.append((name, match.group(0)))
    return hits


def main() -> None:
    parser = argparse.ArgumentParser(description="PII pattern lint")
    parser.add_argument("--paths", nargs="+", default=["apps"], help="Paths to check")
    parser.add_argument("--exclude", nargs="*", default=[], help="Paths to skip")
    parser.add_argument("--fail-on-hit", type=int, default=0)
    args = parser.parse_args()

    violations: Dict[str, List[Tuple[str, str]]] = {}
    for file in iter_files(args.paths, args.exclude):
        hits = scan(file)
        if hits:
            violations[str(file)] = hits

    if not violations:
        print("[pii_lint] no matches")
        return

    for path, hits in violations.items():
        print(f"[pii_lint] {path}")
        for name, value in hits:
            print(f"  - {name}: {value[:40]}")

    if args.fail_on_hit:
        sys.exit(1)


if __name__ == "__main__":
    main()
