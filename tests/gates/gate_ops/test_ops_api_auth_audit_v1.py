"""
Gate OPS — Ops API authentication and audit tests
"""
from apps.ops.api_auth import OpsAPI

def test_no_auth_returns_401():
    """Test unauthenticated request returns 401"""
    api = OpsAPI()
    status, message = api.handle_request("trace-1", None, "read_config", "ops:read")
    
    assert status == 401
    assert message == "Unauthorized"

def test_bearer_auth_success():
    """Test Bearer token authentication succeeds"""
    api = OpsAPI()
    status, message = api.handle_request("trace-2", "Bearer abc123", "read_config", "ops:read")
    
    assert status == 200
    assert "executed" in message

def test_insufficient_scope_returns_403():
    """Test insufficient scope returns 403"""
    api = OpsAPI()
    # Bearer token has ops:read and ops:write, but not deploy:promote
    status, message = api.handle_request("trace-3", "Bearer abc123", "promote", "deploy:promote")
    
    assert status == 403
    assert message == "Forbidden"

def test_audit_log_records_trace_id_and_actor():
    """Test audit log records trace_id and actor"""
    api = OpsAPI()
    api.handle_request("trace-4", "Bearer token", "read_config", "ops:read")
    
    assert len(api.audit_log) == 1
    entry = api.audit_log[0]
    
    assert entry["trace_id"] == "trace-4"
    assert entry["actor"] == "bearer-user"
    assert entry["action"] == "read_config"
    assert entry["status"] == 200

def test_hmac_authentication():
    """Test HMAC authentication"""
    api = OpsAPI(secret_key="test-secret")
    
    # Generate HMAC signature
    import hmac, hashlib
    signature = hmac.new(b"test-secret", b"test-payload", hashlib.sha256).hexdigest()
    
    auth_header = f"HMAC {signature}"
    status, message = api.handle_request("trace-5", auth_header, "write_config", "ops:write")
    
    assert status == 200
