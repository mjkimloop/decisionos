import os, time, yaml, pytest
from pathlib import Path

pytestmark = pytest.mark.gate_sec

def write_map(path, scopes):
    data = {"routes":[{"path":"/ops/cards/*","method":"GET","scopes":scopes}]}
    with open(path,"w",encoding="utf-8") as f:
        yaml.safe_dump(data, f)

def test_rbac_map_state_reload(tmp_path):
    """RBAC 맵 상태 핫리로드 테스트"""
    from apps.policy.rbac_enforce import RbacMapState
    
    mapp = tmp_path / "rbac_map.yaml"
    write_map(mapp, ["ops:read"])
    
    state = RbacMapState(str(mapp), reload_sec=1, require_all=False)
    
    # 초기 로드
    assert len(state.routes) == 1
    assert state.routes[0]["scopes"] == ["ops:read"]
    initial_sha = state.sha
    
    # 맵 변경
    write_map(mapp, ["ops:admin"])
    
    # 리로드 전에는 변경 안됨
    state.ensure_fresh()
    assert state.routes[0]["scopes"] == ["ops:read"]
    
    # 1초 대기 후 리로드
    time.sleep(1.1)
    state.ensure_fresh()
    
    assert state.routes[0]["scopes"] == ["ops:admin"]
    assert state.sha != initial_sha

def test_rbac_scope_parsing():
    """스코프 파싱 테스트"""
    from apps.policy.rbac_enforce import _parse_scopes
    from fastapi import Request
    from unittest.mock import Mock
    
    # 헤더에서 파싱
    req = Mock(spec=Request)
    req.headers = {"x-decisionos-scopes": "ops:read,judge:run"}
    scopes = _parse_scopes(req)
    assert "ops:read" in scopes
    assert "judge:run" in scopes
    
    # 와일드카드
    req.headers = {"x-decisionos-scopes": "*"}
    scopes = _parse_scopes(req)
    assert scopes == ["*"]

def test_rbac_route_matching():
    """라우트 매칭 테스트"""
    from apps.policy.rbac_enforce import _route_match
    
    routes = [
        {"path": "/ops/*", "method": "GET", "scopes": ["ops:read"]},
        {"path": "/ops/cards/*", "method": "GET", "scopes": ["ops:cards"]},
    ]
    
    # 더 구체적인 매칭 우선
    matched = _route_match(routes, "/ops/cards/trends", "GET")
    assert matched["scopes"] == ["ops:cards"]
    
    # 일반 매칭
    matched = _route_match(routes, "/ops/other", "GET")
    assert matched["scopes"] == ["ops:read"]
    
    # 매칭 없음
    matched = _route_match(routes, "/judge/slo", "POST")
    assert matched is None
