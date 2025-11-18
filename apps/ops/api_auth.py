"""
Ops API with Bearer JWT/HMAC authentication, RBAC, and audit logging
"""
import hashlib
import hmac
import json
import os
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class Actor:
    """API actor (user/service)"""
    id: str
    roles: List[str]
    scopes: List[str]

class OpsAPI:
    """
    Ops API with authentication and RBAC.
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or os.environ.get("DECISIONOS_OPS_API_SECRET", "default-secret")
        self.audit_log: List[Dict[str, Any]] = []
    
    def verify_hmac(self, payload: str, signature: str) -> bool:
        """Verify HMAC signature"""
        expected = hmac.new(
            self.secret_key.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected)
    
    def authenticate(self, auth_header: Optional[str]) -> tuple[bool, Optional[Actor]]:
        """
        Authenticate request.
        
        Supports:
        - Bearer <JWT> (simplified, no actual JWT parsing)
        - HMAC <signature>
        
        Returns (authenticated, actor)
        """
        if not auth_header:
            return False, None
        
        parts = auth_header.split(" ", 1)
        if len(parts) != 2:
            return False, None
        
        auth_type, token = parts
        
        if auth_type == "Bearer":
            # Simplified: accept any Bearer token and extract actor ID
            # In production, parse JWT and validate signature
            return True, Actor(id="bearer-user", roles=["admin"], scopes=["ops:read", "ops:write"])
        
        elif auth_type == "HMAC":
            # Verify HMAC signature
            # In production, extract payload from request body
            if self.verify_hmac("test-payload", token):
                return True, Actor(id="hmac-service", roles=["service"], scopes=["ops:write"])
            return False, None
        
        return False, None
    
    def authorize(self, actor: Actor, required_scope: str) -> bool:
        """Check if actor has required scope"""
        return required_scope in actor.scopes
    
    def audit_log_entry(self, trace_id: str, actor: Optional[Actor], action: str, status: int) -> None:
        """Log audit entry"""
        self.audit_log.append({
            "timestamp": time.time(),
            "trace_id": trace_id,
            "actor": actor.id if actor else "anonymous",
            "action": action,
            "status": status
        })
    
    def handle_request(self, trace_id: str, auth_header: Optional[str], action: str, required_scope: str) -> tuple[int, str]:
        """
        Handle API request with auth/authz/audit.
        
        Returns (status_code, message)
        """
        # Authenticate
        authenticated, actor = self.authenticate(auth_header)
        if not authenticated:
            self.audit_log_entry(trace_id, None, action, 401)
            return 401, "Unauthorized"
        
        # Authorize
        if not self.authorize(actor, required_scope):
            self.audit_log_entry(trace_id, actor, action, 403)
            return 403, "Forbidden"
        
        # Execute action (placeholder)
        self.audit_log_entry(trace_id, actor, action, 200)
        return 200, f"Action '{action}' executed by {actor.id}"
