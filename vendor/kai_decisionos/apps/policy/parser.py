from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict

POLICY_RE = re.compile(
    r"(?P<effect>permit|deny)\s*\(\s*(?P<action>[a-zA-Z_][\w\.]*)\s*,\s*(?P<subject>[a-zA-Z_][\w\.]*)\s*,\s*(?P<resource>[a-zA-Z_][\w\.:]*)\s*\)\s*"
    r"(?P<meta>meta\s*\{.*?\}\s*)?"
    r"when\s*\{(?P<when>.*?)\}\s*"
    r"(unless\s*\{(?P<unless>.*?)\}\s*)?$",
    re.DOTALL,
)

META_RE = re.compile(r"meta\s*\{(?P<meta>.*?)\}", re.DOTALL)


@dataclass
class PolicyRule:
    effect: str
    action: str
    subject: str
    resource: str
    when: str
    unless: str | None = None
    priority: int = 0
    policy_id: str | None = None
    purpose: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def parse_policy(text: str) -> PolicyRule:
    match = POLICY_RE.search(text.strip())
    if not match:
        raise ValueError("invalid_policy_syntax")
    metadata = _parse_meta(match.group("meta"))
    return PolicyRule(
        effect="allow" if match.group("effect") == "permit" else "deny",
        action=match.group("action"),
        subject=match.group("subject"),
        resource=match.group("resource"),
        when=match.group("when").strip(),
        unless=(match.group("unless") or "").strip() or None,
        priority=int(metadata.get("priority", 0)),
        policy_id=metadata.get("id"),
        purpose=metadata.get("purpose"),
        metadata=metadata,
    )


def _parse_meta(meta_block: str | None) -> Dict[str, Any]:
    if not meta_block:
        return {}
    meta_match = META_RE.search(meta_block)
    if not meta_match:
        return {}
    raw = meta_match.group("meta")
    meta: Dict[str, Any] = {}
    for line in raw.splitlines():
        line = line.strip().rstrip(",")
        if not line:
            continue
        if ":" not in line:
            raise ValueError("invalid_meta_entry")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key == "priority":
            try:
                meta[key] = int(value)
            except ValueError as exc:
                raise ValueError("invalid_priority") from exc
        else:
            meta[key] = value
    return meta


__all__ = ["PolicyRule", "parse_policy"]
