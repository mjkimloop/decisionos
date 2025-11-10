from __future__ import annotations

import json


def export_json(invoice: dict) -> str:
    return json.dumps(invoice, ensure_ascii=False, indent=2)

