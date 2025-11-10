from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Template

from apps.executor.pipeline import simulate


def _load_template(tpl_path: Path) -> Template:
    txt = tpl_path.read_text(encoding="utf-8")
    return Template(txt)


def _cast_values(rows: list) -> list:
    """Convert CSV string values to appropriate types."""
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
    return rows


def run_report(
    contract: str,
    csv_path: Path,
    label_key: Optional[str],
    out_path: Path,
    template_path: Path,
    json_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Run offline evaluation and generate both HTML and JSON reports.

    Args:
        contract: Contract name
        csv_path: Path to CSV input file
        label_key: Label column name
        out_path: Output HTML path
        template_path: Jinja2 template path
        json_path: Optional JSON metrics output path

    Returns:
        Dictionary with metrics and metadata
    """
    # Load and parse CSV
    rows = list(csv.DictReader(csv_path.open("r", encoding="utf-8")))
    rows = _cast_values(rows)

    # Run simulation
    res = simulate(contract, rows, label_key)

    # Add additional metadata
    report_data = {
        "contract": contract,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "metrics": res["metrics"],
        "metadata": {
            "total_rows": len(rows),
            "label_key": label_key,
            "csv_path": str(csv_path)
        }
    }

    # Generate HTML report
    tpl = _load_template(template_path)
    html = tpl.render(
        now=report_data["timestamp"],
        contract=contract,
        metrics=res["metrics"],
        metadata=report_data["metadata"]
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    # Generate JSON report if requested
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    return report_data
