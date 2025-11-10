from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

TEMPLATE_PATH = Path(__file__).with_name("templates").joinpath("receipt.html")
OUTPUT_DIR = Path("var") / "receipts"


def render_receipt_assets(receipt: Dict[str, object]) -> tuple[str, str]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    receipt_id = receipt.get("id") or f"rc_{int(datetime.now(timezone.utc).timestamp())}"
    context = {
        "receipt_id": receipt_id,
        "charge_id": receipt.get("charge_id"),
        "org_id": receipt.get("org_id"),
        "total": receipt.get("total"),
        "currency": receipt.get("currency"),
        "tax_amount": receipt.get("tax_amount"),
        "issued_at": receipt.get("issued_at"),
    }
    html = _render_template(context)
    pdf_path = OUTPUT_DIR / f"{receipt_id}.pdf"
    json_path = OUTPUT_DIR / f"{receipt_id}.json"
    pdf_path.write_text(html, encoding="utf-8")
    json_path.write_text(json.dumps({**receipt, "rendered_at": datetime.now(timezone.utc).isoformat()}), encoding="utf-8")
    return str(pdf_path), str(json_path)


def _render_template(context: Dict[str, object]) -> str:
    if TEMPLATE_PATH.exists():
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
    else:
        template = """<html><body><h1>Receipt {{receipt_id}}</h1></body></html>"""
    rendered = template
    for key, value in context.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value or ""))
    return rendered
