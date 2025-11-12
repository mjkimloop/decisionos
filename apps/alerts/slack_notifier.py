import json, os, urllib.request
from typing import Dict
from .ratelimit import SlidingWindowRateLimiter
from .router import resolve_channel, rate_key

_limiter = None

def _limiter_for(cfg: Dict) -> SlidingWindowRateLimiter:
    global _limiter
    if _limiter is None:
        rl = cfg.get("rate_limit") or {}
        _limiter = SlidingWindowRateLimiter(rl.get("window_sec", 300), rl.get("max_events", 20))
    return _limiter

def post_slack(cfg: Dict, env: str, reason: str, title: str, body: Dict, dry_run: bool = True) -> Dict:
    ch = os.getenv("DECISIONOS_SLACK_CHANNEL_OVERRIDE") or resolve_channel(env, reason, cfg)
    key = rate_key(env, reason, cfg)
    allowed = _limiter_for(cfg).allow(key)
    payload = {
        "channel": ch,
        "text": f"[{env}] {title}",
        "attachments": [{"color":"#E74C3C" if "fail" in reason else "#2ECC71",
                         "text": "```" + json.dumps(body, ensure_ascii=False, indent=2) + "```"}]
    }
    if not allowed:
        return {"sent": False, "reason": "rate_limited", "channel": ch}
    if dry_run:
        return {"sent": True, "channel": ch, "dry_run": True, "payload": payload}
    req = urllib.request.Request(cfg["webhook"], data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return {"sent": True, "channel": ch, "status": r.status}
