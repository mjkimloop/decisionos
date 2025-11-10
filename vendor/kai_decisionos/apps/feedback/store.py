from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import List, Optional

from .models import FeedbackEntry, FeedbackSubmit


DEFAULT_FEEDBACK_STORE = Path("var/feedback/nps.jsonl")


def _store_path(path: Optional[Path] = None) -> Path:
    actual = path or DEFAULT_FEEDBACK_STORE
    actual.parent.mkdir(parents=True, exist_ok=True)
    return actual


def add_feedback(payload: FeedbackSubmit, store: Optional[Path] = None) -> FeedbackEntry:
    entry = FeedbackEntry.from_submit(payload, identifier=secrets.token_hex(6))
    path = _store_path(store)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry.model_dump(mode="json"), ensure_ascii=False) + "\n")
    return entry


def list_feedback(store: Optional[Path] = None) -> List[FeedbackEntry]:
    path = _store_path(store)
    if not path.exists():
        return []
    entries: List[FeedbackEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entries.append(FeedbackEntry.model_validate_json(line))
        except Exception:
            continue
    return entries


__all__ = ["add_feedback", "list_feedback", "DEFAULT_FEEDBACK_STORE"]

