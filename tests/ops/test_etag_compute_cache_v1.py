import json
import time

from apps.ops.cache.etag_calc import compute_strong_etag


def test_etag_cache_hit_is_fast(tmp_path):
    p = tmp_path / "index.json"
    p.write_text(json.dumps({"a": "b"}), encoding="utf-8")
    salt = "t=-;c=abc;q=deadbeef"

    t0 = time.time()
    e1 = compute_strong_etag(str(p), salt=salt)
    t1 = time.time()
    e2 = compute_strong_etag(str(p), salt=salt)
    t2 = time.time()

    assert e1 == e2
    assert (t2 - t1) < (t1 - t0)
