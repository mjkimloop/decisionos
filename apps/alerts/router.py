from typing import Dict

def resolve_channel(env: str, reason: str, cfg: Dict) -> str:
    # env override
    env_ch = cfg.get("env_channels", {}).get(env)
    # reason routing
    for rule in cfg.get("routing", {}).get("rules", []):
        pref = rule.get("match", {}).get("reason_prefix")
        if pref and reason.startswith(pref):
            return rule.get("channel") or env_ch or cfg.get("default_channel")
    # fallback
    return env_ch or cfg.get("default_channel")

def rate_key(env: str, reason: str, cfg: Dict) -> str:
    key_fmt = (cfg.get("rate_limit") or {}).get("key", "env+reason")
    if key_fmt == "env":
        return env
    if key_fmt == "reason":
        return reason
    return f"{env}:{reason}"
