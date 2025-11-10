from fastapi.testclient import TestClient
from apps.gateway.main import app

client = TestClient(app)

# Test 1: Endpoint protected for users, failing without auth

def test_decide_endpoint_no_auth():
    response = client.post("/api/v1/decide/lead_triage", json={"org_id": "test", "payload": {}})
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

# Test 2: Endpoint protected for admins, failing with a standard user token

def test_simulate_endpoint_wrong_role():
    response = client.post(
        "/api/v1/simulate/lead_triage",
        headers={"Authorization": "Bearer user@example.com"}, # This is the token
        json={"rows": [], "label_key": "converted"}
    )
    assert response.status_code == 403
    assert "Missing required role: admin" in response.json()["detail"]

# Test 3: Consent endpoint, succeeding with a standard user token

def test_consent_endpoint_with_auth():
    response = client.post(
        "/consent",
        headers={"Authorization": "Bearer user@example.com"}, # This is the token
        json={"user_id": "user123", "consents": {"marketing": True}}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "consent updated"
