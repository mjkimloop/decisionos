import json
from apps.policy.rbac_map_hotreload import RbacHotReloader


def test_rbac_hotreload_basic(tmp_path):
    p = tmp_path / "rbac.json"
    p.write_text(json.dumps({"/ops/cards": {"GET": ["ops:read"]}}), encoding="utf-8")
    reloader = RbacHotReloader(str(p))
    reloader.maybe_reload()
    assert reloader.required_scopes_for("/ops/cards", "GET") == ["ops:read"]
    assert reloader.etag
