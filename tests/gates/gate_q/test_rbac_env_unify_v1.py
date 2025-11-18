import textwrap

from apps.policy.rbac_map_hotreload import current_etag, current_map, maybe_reload


def test_rbac_inline_env_yaml(monkeypatch):
    yaml_inline = textwrap.dedent(
        """
      routes:
        - path: /ops/cards/*
          scopes: [ops:read]
    """
    ).strip()
    monkeypatch.setenv("DECISIONOS_RBAC_MAP", yaml_inline)
    monkeypatch.delenv("DECISIONOS_RBAC_MAP_PATH", raising=False)

    before = current_etag()
    maybe_reload()
    after = current_etag()
    assert after and after != before
    m = current_map()
    assert isinstance(m, dict)
    assert m.get("routes")
