from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Sequence

from .models import CatalogItem


SCOPES = {"asset", "dataset", "field"}


@dataclass
class SearchEntry:
    tokens_asset: set[str]
    tokens_dataset: set[str]
    tokens_field: set[str]
    sensitivity: str
    updated_at: datetime


_INDEX: Dict[str, SearchEntry] = {}


def _tokenize(text: str) -> set[str]:
    return {token for token in text.lower().split() if token}


def update(item: CatalogItem) -> None:
    tokens_asset = set()
    tokens_asset |= _tokenize(item.id)
    tokens_asset |= _tokenize(item.name)
    if item.description:
        tokens_asset |= _tokenize(item.description)
    if item.domain:
        tokens_asset |= _tokenize(item.domain)
    if item.owner:
        tokens_asset |= _tokenize(item.owner)
    for tag in item.tags:
        tokens_asset |= _tokenize(tag)
    tokens_field = set()
    for field in item.fields:
        tokens_field |= _tokenize(field.name)
        tokens_field |= _tokenize(field.type)
        if field.description:
            tokens_field |= _tokenize(field.description)
    tokens_dataset = set(tokens_asset)
    if item.type == "dataset":
        tokens_dataset |= tokens_field
    entry = SearchEntry(
        tokens_asset=tokens_asset,
        tokens_dataset=tokens_dataset,
        tokens_field=tokens_field,
        sensitivity=item.sensitivity,
        updated_at=datetime.now(timezone.utc),
    )
    _INDEX[item.id] = entry


def search(
    query: str,
    limit: int = 10,
    scope: str = "asset",
    allowed_sensitivity: Sequence[str] | None = None,
) -> List[str]:
    if limit <= 0:
        return []
    scope = (scope or "asset").lower()
    if scope not in SCOPES:
        raise ValueError(f"invalid_scope:{scope}")
    tokens = _tokenize(query)
    if not tokens:
        return []
    scored: Dict[str, int] = {}
    sensitivity_whitelist = None
    if allowed_sensitivity is not None:
        sensitivity_whitelist = {s.lower() for s in allowed_sensitivity}
    for item_id, entry in _INDEX.items():
        if sensitivity_whitelist and entry.sensitivity.lower() not in sensitivity_whitelist:
            continue
        if scope == "asset":
            haystack = entry.tokens_asset
        elif scope == "dataset":
            haystack = entry.tokens_dataset
        else:
            haystack = entry.tokens_field
        score = len(tokens & haystack)
        if score:
            scored[item_id] = score
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    results = sorted(
        scored.items(),
        key=lambda kv: (-kv[1], -_INDEX[kv[0]].updated_at.timestamp() if kv[0] in _INDEX else -epoch.timestamp()),
    )
    return [item_id for item_id, _ in results[:limit]]


def clear() -> None:
    _INDEX.clear()


__all__ = ["update", "search", "clear", "SCOPES"]
