import pytest

pytestmark = [pytest.mark.gate_aj]

import time

from apps.judge.replay_plugins import SQLiteReplayStore


def test_sqlite_replay_store_roundtrip(tmp_path):
    store = SQLiteReplayStore(path=str(tmp_path / "replay.sqlite"))
    ts = int(time.time())
    assert store.seen_or_insert("k1", "nonce1", ts) is False
    assert store.seen_or_insert("k1", "nonce1", ts) is True
