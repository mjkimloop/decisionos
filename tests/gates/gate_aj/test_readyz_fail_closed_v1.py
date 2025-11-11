import importlib
from starlette.testclient import TestClient
import pytest

pytestmark = [pytest.mark.gate_aj]

def test_readyz_fail_closed(monkeypatch):
    # server 모듈이 check_ready를 직접 참조하므로 모듈 네임스페이스에서 패치
    import apps.judge.server as server
    
    # 준비 불가 상황 시뮬레이션
    def fake_check_ready(key_loader=None, replay_store=None):
        return False, {"reasons": ["keys.stale"]}
    
    monkeypatch.setattr("apps.judge.server.check_ready", fake_check_ready)
    importlib.reload(server)

    client = TestClient(server.app)
    resp = client.get("/readyz")
    assert resp.status_code == 503
