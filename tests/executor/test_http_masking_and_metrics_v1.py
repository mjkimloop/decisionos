from apps.executor.plugins import _mask_headers, _mask_json


def test_masking_utils():
    h = {"Authorization": "Bearer x", "X-Api-Key": "zzz", "X-Other": "ok"}
    m = _mask_headers(h)
    assert m["Authorization"] == "***"
    assert m["X-Other"] == "ok"
    j = {"password": "a", "data": "b"}
    masked = _mask_json(j)
    assert masked["password"] == "***"
