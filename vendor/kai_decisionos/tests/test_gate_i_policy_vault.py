from __future__ import annotations

from fastapi.testclient import TestClient

from apps.gateway.main import app

client = TestClient(app)
HEADERS = {"X-Api-Key":"dev-key","X-Role":"admin","X-Tenant-ID":"demo-tenant"}


def test_policy_validate_simulate_and_enforce():
    policy = {
        "name": "basic",
        "rules": [
            {"when": "payload.get('credit_score',0) < 550", "action": "deny", "reason": "low score"},
            {"when": "payload.get('dti',1.0) > 0.6", "action": "deny", "reason": "high dti"},
            {"when": "payload.get('income_verified') == False", "action": "review", "reason": "docs"},
        ],
    }
    v = client.post('/api/v1/policy/validate', headers=HEADERS, json={"policy": policy})
    assert v.status_code == 200 and v.json().get('valid') is True
    rows = [
        {"credit_score": 540, "dti": 0.3, "income_verified": True},
        {"credit_score": 700, "dti": 0.7, "income_verified": True},
        {"credit_score": 700, "dti": 0.3, "income_verified": False},
    ]
    s = client.post('/api/v1/policy/simulate', headers=HEADERS, json={"policy": policy, "rows": rows})
    assert s.status_code == 200 and s.json().get('n') == 3
    e = client.post('/api/v1/policy/enforce', headers=HEADERS, json={"stage":"pre","policy":policy,"payload":rows[0]})
    assert e.status_code == 200 and e.json().get('action') in {"deny","review","allow"}


def test_vault_set_get_and_hitl_ui():
    r = client.post('/api/v1/vault/set', headers=HEADERS, json={"key":"API_KEY","value":"xyz"})
    assert r.status_code == 200
    g = client.get('/api/v1/vault/get', headers=HEADERS, params={"key":"API_KEY"})
    assert g.status_code == 200 and g.json().get('value') == 'xyz'
    ui = client.get('/api/v1/hitl/ui', headers=HEADERS)
    assert ui.status_code == 200 and 'HITL' in ui.text
