import os, pytest
from apps.storage.etag_store import load_store_from_env, InMemoryETagStore

def test_memory_store_default():
    os.environ.pop("DECISIONOS_ETAG_BACKEND", None)
    st = load_store_from_env()
    assert isinstance(st, InMemoryETagStore)
    assert st.get("k") is None
    st.set("k","e1")
    assert st.get("k") == "e1"
    assert st.compare_and_set("k","e1","e2")
    assert st.get("k") == "e2"
    assert not st.compare_and_set("k","wrong","e3")
