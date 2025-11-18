import json

from apps.ops.api.cards_delta import _compute_etag_seed


def test_etag_seed_changes_on_reason_top_change(tmp_path):
    base = {
        "generated_at": "2025-11-18T00:00:00Z",
        "buckets": [{"ts": "2025-11-18T00:00:00Z", "reasons": {"perf": 1, "infra-latency": 1}}],
    }
    f1 = tmp_path / "index1.json"
    f1.write_text(json.dumps(base), encoding="utf-8")
    mod = dict(base)
    mod["buckets"] = [{"ts": "2025-11-18T00:00:00Z", "reasons": {"perf": 1, "infra-latency": 2}}]
    f2 = tmp_path / "index2.json"
    f2.write_text(json.dumps(mod), encoding="utf-8")

    s1 = _compute_etag_seed(index_path=str(f1), tenant="tA", catalog_sha="abc", query_hash="q")
    s2 = _compute_etag_seed(index_path=str(f2), tenant="tA", catalog_sha="abc", query_hash="q")
    assert s1 != s2
