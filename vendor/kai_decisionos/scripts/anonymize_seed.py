#!/usr/bin/env python
from __future__ import annotations

import csv
import sys
from pathlib import Path

from apps.security.anonymizer import anonymize_record


def anonymize_csv(src: Path, dst: Path):
    rows = list(csv.DictReader(src.open('r', encoding='utf-8')))
    out = dst.open('w', encoding='utf-8', newline='')
    try:
        if not rows:
            print('No rows')
            return
        w = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(anonymize_record(r))
    finally:
        out.close()


def main():
    if len(sys.argv) < 3:
        print('usage: python scripts/anonymize_seed.py <src.csv> <dst.csv>')
        sys.exit(2)
    anonymize_csv(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == '__main__':
    main()
