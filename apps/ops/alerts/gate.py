from __future__ import annotations
import os
from typing import Dict, Any
from .slack import post_card

def should_alert(summary: Dict[str, Any]) -> bool:
    min_flags = int(os.environ.get("ALERTS_GATE_MIN_FLAGS", "1"))
    min_score = float(os.environ.get("ALERTS_GATE_MIN_SCORE", "5.0"))
    for b in summary.get("buckets", []):
        if b.get("anomaly", {}).get("triggered"):
            score = b.get("score", 0.0) or b.get("bucket_score", 0.0)
            flags = len(b.get("anomaly", {}).get("flags", []))
            if flags >= min_flags and score >= min_score:
                return True
    return False

def build_payload(summary: Dict[str, Any]) -> dict:
    tb = summary.get("top_buckets", [])[:1]
    title = "DecisionOS: Anomaly Triggered"
    if tb:
        title += f" @ {tb[0].get('end', '')}"
    return {
        "text": title,
        "attachments": [{"color": "#ee0701", "fields": [
            {"title": "flags", "value": str(len(summary.get('buckets', [])))},
            {"title": "top-impact", "value": str(summary.get("top_labels", "[]"))}
        ]}]
    }

def run_alert_gate(summary: Dict[str, Any]) -> int:
    scopes = os.environ.get("DECISIONOS_ALLOW_SCOPES", "")
    if "ops:alert" not in scopes and "*" not in scopes:
        return 3
    if not should_alert(summary):
        return 0
    wh = os.environ.get("ALERTS_SLACK_WEBHOOK", "")
    if not wh:
        return 0
    try:
        code = post_card(wh, build_payload(summary))
        return 0 if 200 <= code < 300 else 2
    except Exception:
        return 2
