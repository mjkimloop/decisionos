from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import List, Optional

from .models import BacklogItem, BacklogSubmit
from .rice import compute_rice


DEFAULT_BACKLOG_STORE = Path("var/backlog/items.jsonl")


def _store_path(path: Optional[Path] = None) -> Path:
    actual = path or DEFAULT_BACKLOG_STORE
    actual.parent.mkdir(parents=True, exist_ok=True)
    return actual


def add_item(payload: BacklogSubmit, store: Optional[Path] = None) -> BacklogItem:
    rice_score = compute_rice(payload.reach, payload.impact, payload.confidence, payload.effort)
    item = BacklogItem.from_submit(payload, identifier=secrets.token_hex(6), rice=rice_score)
    path = _store_path(store)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(item.model_dump(mode="json"), ensure_ascii=False) + "\n")
    return item


def list_items(store: Optional[Path] = None) -> List[BacklogItem]:
    path = _store_path(store)
    if not path.exists():
        return []
    items: List[BacklogItem] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            items.append(BacklogItem.model_validate_json(line))
        except Exception:
            continue
    return items


__all__ = ["add_item", "list_items", "DEFAULT_BACKLOG_STORE"]

