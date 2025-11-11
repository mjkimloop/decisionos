import pytest
from apps.ops.cards.aggregation import aggregate_reasons, label_catalog_hash

@pytest.mark.gate_ops
def test_topn_and_weights_shape():
    reasons = ["reason:infra-latency"]*3 + ["reason:infra-error"]*2 + ["reason:perf"] + ["reason:canary"]
    out = aggregate_reasons(reasons, top=3)
    assert "groups" in out and "weighted" in out
    assert len(out["top_groups"]) <= 3
    assert len(out["top_labels"]) <= 3
    # 가중치 키 존재(예: Infra, Perf 등)
    assert isinstance(out["weights"], dict)
    # top_groups와 top_labels 구조 확인
    assert all("name" in g and "score" in g for g in out["top_groups"])
    assert all("name" in l and "count" in l for l in out["top_labels"])

@pytest.mark.gate_ops
def test_label_catalog_hash_format():
    sha = label_catalog_hash()
    assert isinstance(sha, str) and len(sha) >= 40
    # SHA256은 정확히 64자 hex
    assert len(sha) == 64
    assert all(c in "0123456789abcdef" for c in sha)
