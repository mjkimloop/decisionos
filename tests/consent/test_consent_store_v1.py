import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from apps.consent.store import InMemoryConsentStore, ConsentRecord


@pytest.mark.asyncio
async def test_grant_and_chain_and_ttl():
    store = InMemoryConsentStore()
    now = datetime.now(timezone.utc).isoformat()
    rec1 = ConsentRecord(subject_id="s1", doc_hash="hash1111", scope="a", ttl_sec=60, granted_at=now)
    out1 = await store.grant(rec1)
    assert out1.prev_hash == ""
    assert out1.curr_hash

    rec2 = ConsentRecord(subject_id="s1", doc_hash="hash2222", scope="b", ttl_sec=60, granted_at=now)
    out2 = await store.grant(rec2)
    assert out2.prev_hash == out1.curr_hash

    listed = await store.list("s1")
    assert len(listed) == 2


@pytest.mark.asyncio
async def test_revoke_and_expire():
    store = InMemoryConsentStore()
    now = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    rec = ConsentRecord(subject_id="s2", doc_hash="hash3333", scope="a", ttl_sec=60, granted_at=now)
    await store.grant(rec)
    # TTL 만료로 list 결과 없음
    listed = await store.list("s2")
    assert listed == []

    # 재grant 후 revoke
    fresh = ConsentRecord(subject_id="s2", doc_hash="hash4444", scope="a", ttl_sec=60, granted_at=datetime.now(timezone.utc).isoformat())
    await store.grant(fresh)
    await store.revoke("s2", "hash4444")
    listed = await store.list("s2")
    assert listed == []
    with pytest.raises(LookupError):
        await store.revoke("s2", "missing")
