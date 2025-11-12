from __future__ import annotations
import json
import os
import urllib.request
from typing import List, Dict, Any

def load_playbooks(path: str = "configs/playbooks/actions.json") -> Dict[str, List[str]]:
    """Load playbook actions from config file"""
    if not os.path.exists(path):
        return {"default": ["Open incident ticket", "Notify on-call"]}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_playbook_actions(reason: str, playbooks: Dict[str, List[str]]) -> List[str]:
    """Get playbook actions for a given reason, fallback to default"""
    return playbooks.get(reason, playbooks.get("default", ["Open incident ticket"]))

def _post(url: str, payload: Dict[str, Any]) -> None:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as _:
        return

def dispatch_alerts(events: List[Dict[str, Any]], routes_cfg: Dict[str, Any], dry_run: bool = True) -> None:
    """
    events: [{"level":"warn|critical","reason":"reason:budget-burn","message":"...","evidence_link":"..."}]
    routes_cfg: {"slack":{"webhook_env":"DECISIONOS_SLACK_WEBHOOK","channel":"#ops"}, "webhook":[{"url_env":"..."}], "filters":{"min_severity":"warn"}}
    """
    if not events:
        return
    min_sev = (routes_cfg.get("filters", {}) or {}).get("min_severity", "warn")
    sev_rank = {"warn": 1, "critical": 2}
    target = [e for e in events if sev_rank.get(e.get("level","warn"),1) >= sev_rank.get(min_sev,1)]

    if not target:
        return

    # Slack
    slack = routes_cfg.get("slack")
    if slack:
        hook_env = slack.get("webhook_env")
        url = os.environ.get(hook_env or "", "")
        if url:
            for e in target:
                payload = {"text": f"[{e.get('level').upper()}] {e.get('reason')} — {e.get('message')}\n{e.get('evidence_link','')}"}
                if dry_run:
                    continue
                _post(url, payload)

    # Generic webhooks
    for wh in routes_cfg.get("webhook", []):
        url = os.environ.get(wh.get("url_env",""), "")
        if not url:
            continue
        for e in target:
            payload = {"level": e.get("level"), "reason": e.get("reason"), "message": e.get("message"), "link": e.get("evidence_link","")}
            if dry_run:
                continue
            _post(url, payload)
