from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from apps.analytics.leading_kpis import compute_leading_kpis
from apps.security.anonymizer import anonymize_record


def load_rows(csv_path: Path) -> list[dict]:
    import csv
    rows = list(csv.DictReader(csv_path.open("r", encoding="utf-8")))
    return rows


def generate_seal_report(csv_path: Path, out_json: Path) -> dict:
    rows = load_rows(csv_path)
    kpis = compute_leading_kpis(rows, label_key="converted")
    # preview anonymized sample (3 rows)
    preview = [anonymize_record(r) for r in rows[:3]]
    report = {"kpis": kpis, "preview": preview}
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report

