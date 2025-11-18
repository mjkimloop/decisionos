"""Tests for Cards API delta ETag flow."""
from __future__ import annotations

import pytest


@pytest.mark.gate_q
def test_delta_computation_added():
    """Test: Delta detects added cards."""
    from apps.ops.cache.etag_delta import compute_cards_delta

    base = {"cards": [{"id": "c1", "score": 10}]}
    now = {"cards": [{"id": "c1", "score": 10}, {"id": "c2", "score": 20}]}

    delta = compute_cards_delta(base, now)

    assert delta is not None
    assert len(delta["added"]) == 1
    assert delta["added"][0]["id"] == "c2"
    assert len(delta["removed"]) == 0
    assert len(delta["updated"]) == 0


@pytest.mark.gate_q
def test_delta_computation_removed():
    """Test: Delta detects removed cards."""
    from apps.ops.cache.etag_delta import compute_cards_delta

    base = {"cards": [{"id": "c1", "score": 10}, {"id": "c2", "score": 20}]}
    now = {"cards": [{"id": "c1", "score": 10}]}

    delta = compute_cards_delta(base, now)

    assert delta is not None
    assert len(delta["added"]) == 0
    assert len(delta["removed"]) == 1
    assert delta["removed"][0]["id"] == "c2"
    assert len(delta["updated"]) == 0


@pytest.mark.gate_q
def test_delta_computation_updated():
    """Test: Delta detects updated cards."""
    from apps.ops.cache.etag_delta import compute_cards_delta

    base = {"cards": [{"id": "c1", "score": 10}]}
    now = {"cards": [{"id": "c1", "score": 20}]}

    delta = compute_cards_delta(base, now)

    assert delta is not None
    assert len(delta["added"]) == 0
    assert len(delta["removed"]) == 0
    assert len(delta["updated"]) == 1
    assert delta["updated"][0]["id"] == "c1"
    assert delta["updated"][0]["score"] == 20


@pytest.mark.gate_q
def test_delta_computation_combined():
    """Test: Delta detects combined changes."""
    from apps.ops.cache.etag_delta import compute_cards_delta

    base = {
        "cards": [
            {"id": "c1", "score": 10},
            {"id": "c2", "score": 20},
            {"id": "c3", "score": 30},
        ]
    }
    now = {
        "cards": [
            {"id": "c1", "score": 15},  # Updated
            {"id": "c3", "score": 30},  # Unchanged
            {"id": "c4", "score": 40},  # Added
        ]
    }

    delta = compute_cards_delta(base, now)

    assert delta is not None
    assert len(delta["added"]) == 1
    assert delta["added"][0]["id"] == "c4"
    assert len(delta["removed"]) == 1
    assert delta["removed"][0]["id"] == "c2"
    assert len(delta["updated"]) == 1
    assert delta["updated"][0]["id"] == "c1"


@pytest.mark.gate_q
def test_delta_apply():
    """Test: Apply delta to base snapshot."""
    from apps.ops.cache.etag_delta import apply_cards_delta, compute_cards_delta

    base = {"cards": [{"id": "c1", "score": 10}]}
    now = {"cards": [{"id": "c1", "score": 20}, {"id": "c2", "score": 30}]}

    delta = compute_cards_delta(base, now)
    result = apply_cards_delta(base, delta)

    # Should match 'now'
    assert len(result["cards"]) == 2
    card_ids = {c["id"] for c in result["cards"]}
    assert card_ids == {"c1", "c2"}


@pytest.mark.gate_q
def test_delta_is_applicable():
    """Test: Check if delta has changes."""
    from apps.ops.cache.etag_delta import compute_cards_delta, is_delta_applicable

    base = {"cards": [{"id": "c1", "score": 10}]}
    now_same = {"cards": [{"id": "c1", "score": 10}]}
    now_diff = {"cards": [{"id": "c1", "score": 20}]}

    delta_same = compute_cards_delta(base, now_same)
    delta_diff = compute_cards_delta(base, now_diff)

    assert not is_delta_applicable(delta_same)
    assert is_delta_applicable(delta_diff)


@pytest.mark.gate_q
def test_delta_invalid_input():
    """Test: Delta computation handles invalid input."""
    from apps.ops.cache.etag_delta import compute_cards_delta

    # Invalid input
    assert compute_cards_delta({}, {}) is None
    assert compute_cards_delta({"cards": "invalid"}, {"cards": []}) is None
    assert compute_cards_delta({"cards": []}, {"cards": "invalid"}) is None


@pytest.mark.gate_q
def test_snapshot_store_memory():
    """Test: In-memory snapshot store."""
    import asyncio
    from apps.ops.cache.snapshot_store import InMemorySnapshotStore

    store = InMemorySnapshotStore()

    async def test():
        # Set
        await store.set("etag1", {"data": "test"}, ttl_sec=60)

        # Get
        data = await store.get("etag1")
        assert data == {"data": "test"}

        # Delete
        await store.delete("etag1")
        data = await store.get("etag1")
        assert data is None

    asyncio.run(test())


@pytest.mark.gate_q
def test_snapshot_store_missing():
    """Test: Snapshot store returns None for missing ETags."""
    import asyncio
    from apps.ops.cache.snapshot_store import InMemorySnapshotStore

    store = InMemorySnapshotStore()

    async def test():
        data = await store.get("nonexistent")
        assert data is None

    asyncio.run(test())
