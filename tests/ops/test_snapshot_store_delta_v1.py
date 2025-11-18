from apps.ops.cache.snapshot_store import build_snapshot_store, InMemorySnapshotStore
from apps.ops.cache.delta import compute_etag, make_delta_etag, not_modified
import pytest

@pytest.mark.asyncio
async def test_snapshot_and_delta():
    st = build_snapshot_store()
    assert isinstance(st, InMemorySnapshotStore)
    payload = {"a":1}
    etag1 = compute_etag(payload)
    await st.set(etag1, payload)
    got = await st.get(etag1)
    assert got and got.get("a") == 1
    # delta
    newp = {"a":2}
    etag2 = make_delta_etag(etag1, newp)
    assert etag2 != etag1
    assert not not_modified("zzz", etag2)
    assert not_modified(etag2, etag2)
