import pytest
from apps.ops.cards.etag_v2 import build_cards_etag_key, compute_cards_etag

@pytest.mark.gate_ops
def test_etag_changes_on_seasonality():
    k1 = build_cards_etag_key("2025-01-01T00:00:00Z", "2025-01-01T12:00:00Z",
                              bucket="hour", seasonality="auto",
                              delta_enabled=True, delta_require_same_window=False,
                              continuity_token=None)
    k2 = build_cards_etag_key("2025-01-01T00:00:00Z", "2025-01-01T12:00:00Z",
                              bucket="hour", seasonality="off",
                              delta_enabled=True, delta_require_same_window=False,
                              continuity_token=None)
    assert compute_cards_etag(k1) != compute_cards_etag(k2)

@pytest.mark.gate_ops
def test_etag_changes_on_bucket():
    k1 = build_cards_etag_key("2025-01-01T00:00:00Z", "2025-01-01T12:00:00Z",
                              bucket="hour", seasonality="auto",
                              delta_enabled=True, delta_require_same_window=False,
                              continuity_token=None)
    k2 = build_cards_etag_key("2025-01-01T00:00:00Z", "2025-01-01T12:00:00Z",
                              bucket="day", seasonality="auto",
                              delta_enabled=True, delta_require_same_window=False,
                              continuity_token=None)
    assert compute_cards_etag(k1) != compute_cards_etag(k2)

@pytest.mark.gate_ops
def test_etag_same_for_identical_params():
    k1 = build_cards_etag_key("2025-01-01T00:00:00Z", "2025-01-01T12:00:00Z",
                              bucket="hour", seasonality="auto",
                              delta_enabled=True, delta_require_same_window=False,
                              continuity_token=None)
    k2 = build_cards_etag_key("2025-01-01T00:00:00Z", "2025-01-01T12:00:00Z",
                              bucket="hour", seasonality="auto",
                              delta_enabled=True, delta_require_same_window=False,
                              continuity_token=None)
    assert compute_cards_etag(k1) == compute_cards_etag(k2)
