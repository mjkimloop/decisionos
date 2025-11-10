from __future__ import annotations

from pathlib import Path
import csv
from typing import Optional
from jinja2 import Template

from apps.executor.pipeline import simulate


HTML_TPL = Template(
    """
<!doctype html>
<html><head><meta charset="utf-8"><title>Offline Eval</title>
<style>body{font-family:sans-serif;max-width:720px;margin:2rem auto}</style></head>
<body>
  <h1>Simulation Metrics</h1>
  <ul>
    <li>Reject Precision: {{ m.reject_precision | round(4) }}</li>
    <li>Reject Recall: {{ m.reject_recall | round(4) }}</li>
    <li>Review Rate: {{ m.review_rate | round(4) }}</li>
  </ul>
</body></html>
"""
)


def run_report(contract: str, csv_path: Path, label_key: Optional[str], out_path: Path) -> Path:
    rows = list(csv.DictReader(csv_path.open("r", encoding="utf-8")))
    for r in rows:
        for k, v in list(r.items()):
            if v in ("True", "False"):
                r[k] = v == "True"
            else:
                try:
                    if "." in v:
                        r[k] = float(v)
                    else:
                        r[k] = int(v)
                except Exception:
                    pass
    res = simulate(contract, rows, label_key)
    html = HTML_TPL.render(m=res["metrics"])  # type: ignore
    out_path.write_text(html, encoding="utf-8")
    return out_path

