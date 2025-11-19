from apps.executor.http_client import get_http_client


def test_http_client_singleton():
    c1 = get_http_client()
    c2 = get_http_client()
    assert c1 is c2
