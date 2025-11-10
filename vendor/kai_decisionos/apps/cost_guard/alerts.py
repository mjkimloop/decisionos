from __future__ import annotations


def check_margin_alert(margin_pct: float, threshold: float = 40.0) -> dict:
    return {"alert": margin_pct < threshold, "threshold": threshold}

