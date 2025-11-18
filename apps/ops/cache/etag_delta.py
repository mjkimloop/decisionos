"""ETag delta computation for incremental card updates.

Provides utilities for computing and applying deltas between card snapshots.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List


def compute_cards_delta(base: Dict[str, Any], now: Dict[str, Any]) -> Dict[str, Any] | None:
    """Compute delta between two card snapshots.

    Args:
        base: Base snapshot (older)
        now: Current snapshot (newer)

    Returns:
        Delta dict with added/removed/updated cards, or None if incompatible
    """
    if not isinstance(base, dict) or not isinstance(now, dict):
        return None

    b_cards = base.get("cards")
    n_cards = now.get("cards")

    if not isinstance(b_cards, list) or not isinstance(n_cards, list):
        return None

    def _index(lst: List[Dict]) -> Dict[str, Dict]:
        """Index cards by ID."""
        out = {}
        for it in lst:
            if isinstance(it, dict) and "id" in it:
                out[str(it["id"])] = it
        return out

    bi = _index(b_cards)
    ni = _index(n_cards)

    added = []
    removed = []
    updated = []

    # Find added and updated
    for k, v in ni.items():
        if k not in bi:
            added.append(v)
        else:
            # Compare JSON representation
            if json.dumps(v, sort_keys=True) != json.dumps(bi[k], sort_keys=True):
                updated.append(v)

    # Find removed
    for k, v in bi.items():
        if k not in ni:
            removed.append({"id": k})

    return {
        "added": added,
        "removed": removed,
        "updated": updated,
    }


def apply_cards_delta(base: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
    """Apply delta to base snapshot to get new snapshot.

    Args:
        base: Base snapshot
        delta: Delta with added/removed/updated

    Returns:
        New snapshot after applying delta
    """
    if not isinstance(base, dict) or not isinstance(delta, dict):
        return base

    cards = base.get("cards", [])
    if not isinstance(cards, list):
        return base

    # Index existing cards
    card_map = {}
    for card in cards:
        if isinstance(card, dict) and "id" in card:
            card_map[str(card["id"])] = card

    # Apply removed
    for removed in delta.get("removed", []):
        if isinstance(removed, dict) and "id" in removed:
            card_map.pop(str(removed["id"]), None)

    # Apply updated
    for updated in delta.get("updated", []):
        if isinstance(updated, dict) and "id" in updated:
            card_map[str(updated["id"])] = updated

    # Apply added
    for added in delta.get("added", []):
        if isinstance(added, dict) and "id" in added:
            card_map[str(added["id"])] = added

    # Rebuild cards list (preserve order where possible)
    result = base.copy()
    result["cards"] = list(card_map.values())

    return result


def is_delta_applicable(delta: Dict[str, Any]) -> bool:
    """Check if delta has any changes.

    Args:
        delta: Delta dict

    Returns:
        True if delta has any added/removed/updated items
    """
    if not isinstance(delta, dict):
        return False

    added = delta.get("added", [])
    removed = delta.get("removed", [])
    updated = delta.get("updated", [])

    return bool(added or removed or updated)
