import textwrap

from apps.policy import rbac_map_hotreload as hot


def test_rbac_map_hotreload_metrics(tmp_path, monkeypatch):
    p = tmp_path / "rbac_map.yaml"
    monkeypatch.setenv("DECISIONOS_RBAC_MAP_PATH", str(p))
    monkeypatch.setenv("DECISIONOS_RBAC_MAP_CHECK_SEC", "0")

    hot.maybe_reload()
    e0 = hot.current_etag()

    p.write_text(
        textwrap.dedent(
            """
            routes:
              - path: /ops/cards/*
                scopes: [ops:read]
            """
        ).strip(),
        encoding="utf-8",
    )
    hot.maybe_reload()
    e1 = hot.current_etag()
    assert e1

    hot.maybe_reload()
    e2 = hot.current_etag()
    assert e2 == e1
