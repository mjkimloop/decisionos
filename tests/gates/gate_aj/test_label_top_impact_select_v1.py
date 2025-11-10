import pytest

from scripts.ci.label_top_impact import LABEL_PREFIX, _select_labels

pytestmark = [pytest.mark.gate_aj]


def test_select_labels_from_trend():
    trend = {"total_top": [["perf.p95_over", 5], ["quota.forbidden_action", 3]]}
    labels = _select_labels(trend, topK=2)
    assert labels == [
        f"{LABEL_PREFIX}perf.p95_over",
        f"{LABEL_PREFIX}quota.forbidden_action",
    ]
